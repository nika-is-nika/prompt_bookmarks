"""
Database layer for Prompt Bookmarks.

Handles all database operations including CRUD for prompts, folders, and tags.
"""

import os
from typing import List, Optional, Tuple
from pathlib import Path
from sqlalchemy import create_engine, and_, or_
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError

from .models import (
    Base, PromptDB, FolderDB, TagDB, 
    Prompt, Folder, Tag, PromptCreate, PromptUpdate, PromptSearch
)


class Database:
    """Database management class."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize database connection."""
        if db_path is None:
            # Default to user's data directory
            data_dir = Path.home() / ".prompt_bookmarks"
            data_dir.mkdir(exist_ok=True)
            db_path = str(data_dir / "prompts.db")
        
        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}")
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Create tables
        Base.metadata.create_all(bind=self.engine)
        
        # Initialize default data
        self._initialize_defaults()
    
    def _initialize_defaults(self):
        """Initialize default folders and tags."""
        with self.get_session() as session:
            # Create root folder if it doesn't exist
            root = session.query(FolderDB).filter_by(path="/").first()
            if not root:
                root = FolderDB(name="Root", path="/", parent_id=None)
                session.add(root)
                session.commit()
            
            # Create default AI tool tags
            default_tags = [
                ("claude", "ai_tool", "#7C3AED"),
                ("chatgpt", "ai_tool", "#10B981"),
                ("perplexity", "ai_tool", "#3B82F6"),
                ("gemini", "ai_tool", "#F59E0B"),
                ("coding", "topic", "#EF4444"),
                ("writing", "topic", "#8B5CF6"),
                ("analysis", "topic", "#06B6D4"),
            ]
            
            for tag_name, category, color in default_tags:
                existing_tag = session.query(TagDB).filter_by(name=tag_name).first()
                if not existing_tag:
                    tag = TagDB(name=tag_name, category=category, color=color)
                    session.add(tag)
            
            session.commit()
    
    def get_session(self) -> Session:
        """Get database session."""
        return self.SessionLocal()
    
    # Folder operations
    def create_folder(self, name: str, path: str, parent_path: Optional[str] = None) -> Folder:
        """Create a new folder."""
        with self.get_session() as session:
            parent_id = None
            if parent_path:
                parent = session.query(FolderDB).filter_by(path=parent_path).first()
                if parent:
                    parent_id = parent.id
            
            folder_db = FolderDB(name=name, path=path, parent_id=parent_id)
            session.add(folder_db)
            session.commit()
            session.refresh(folder_db)
            
            return Folder.model_validate(folder_db)
    
    def get_folder_by_path(self, path: str) -> Optional[Folder]:
        """Get folder by path."""
        with self.get_session() as session:
            folder_db = session.query(FolderDB).filter_by(path=path).first()
            if folder_db:
                return Folder.model_validate(folder_db)
            return None
    
    def list_folders(self, parent_path: Optional[str] = None) -> List[Folder]:
        """List folders, optionally filtered by parent."""
        with self.get_session() as session:
            query = session.query(FolderDB)
            
            if parent_path is not None:
                parent = session.query(FolderDB).filter_by(path=parent_path).first()
                if parent:
                    query = query.filter_by(parent_id=parent.id)
                else:
                    return []
            
            folders_db = query.all()
            folders = []
            
            for folder_db in folders_db:
                folder = Folder.model_validate(folder_db)
                # Count prompts in this folder
                folder.prompt_count = session.query(PromptDB).filter_by(folder_id=folder_db.id).count()
                folders.append(folder)
            
            return folders
    
    def delete_folder(self, path: str) -> bool:
        """Delete a folder and optionally move prompts to parent."""
        with self.get_session() as session:
            folder = session.query(FolderDB).filter_by(path=path).first()
            if not folder:
                return False
            
            # Move prompts to parent folder
            parent_id = folder.parent_id
            session.query(PromptDB).filter_by(folder_id=folder.id).update({"folder_id": parent_id})
            
            # Delete folder
            session.delete(folder)
            session.commit()
            return True
    
    # Tag operations
    def create_tag(self, name: str, category: Optional[str] = None, color: Optional[str] = None) -> Tag:
        """Create a new tag."""
        with self.get_session() as session:
            tag_db = TagDB(name=name, category=category, color=color)
            session.add(tag_db)
            session.commit()
            session.refresh(tag_db)
            
            return Tag.model_validate(tag_db)
    
    def get_tag_by_name(self, name: str) -> Optional[Tag]:
        """Get tag by name."""
        with self.get_session() as session:
            tag_db = session.query(TagDB).filter_by(name=name).first()
            if tag_db:
                return Tag.model_validate(tag_db)
            return None
    
    def list_tags(self, category: Optional[str] = None) -> List[Tag]:
        """List all tags, optionally filtered by category."""
        with self.get_session() as session:
            query = session.query(TagDB)
            if category:
                query = query.filter_by(category=category)
            
            tags_db = query.all()
            return [Tag.model_validate(tag_db) for tag_db in tags_db]
    
    def delete_tag(self, name: str) -> bool:
        """Delete a tag."""
        with self.get_session() as session:
            tag = session.query(TagDB).filter_by(name=name).first()
            if not tag:
                return False
            
            session.delete(tag)
            session.commit()
            return True
    
    # Prompt operations
    def create_prompt(self, prompt_data: PromptCreate) -> Prompt:
        """Create a new prompt."""
        with self.get_session() as session:
            # Get or create folder
            folder_id = None
            if prompt_data.folder_path:
                folder = session.query(FolderDB).filter_by(path=prompt_data.folder_path).first()
                if not folder:
                    # Create folder hierarchy
                    folder = self._create_folder_hierarchy(session, prompt_data.folder_path)
                folder_id = folder.id
            
            # Create prompt
            prompt_db = PromptDB(
                title=prompt_data.title,
                content=prompt_data.content,
                description=prompt_data.description,
                folder_id=folder_id
            )
            session.add(prompt_db)
            session.flush()  # Get the ID
            
            # Add tags
            for tag_name in prompt_data.tags:
                tag = session.query(TagDB).filter_by(name=tag_name).first()
                if not tag:
                    tag = TagDB(name=tag_name, category="custom")
                    session.add(tag)
                    session.flush()
                prompt_db.tags.append(tag)
            
            session.commit()
            session.refresh(prompt_db)
            
            return self._prompt_db_to_pydantic(session, prompt_db)
    
    def get_prompt(self, prompt_id: int) -> Optional[Prompt]:
        """Get prompt by ID."""
        with self.get_session() as session:
            prompt_db = session.query(PromptDB).filter_by(id=prompt_id).first()
            if prompt_db:
                return self._prompt_db_to_pydantic(session, prompt_db)
            return None
    
    def update_prompt(self, prompt_id: int, prompt_data: PromptUpdate) -> Optional[Prompt]:
        """Update a prompt."""
        with self.get_session() as session:
            prompt_db = session.query(PromptDB).filter_by(id=prompt_id).first()
            if not prompt_db:
                return None
            
            # Update fields
            if prompt_data.title is not None:
                prompt_db.title = prompt_data.title
            if prompt_data.content is not None:
                prompt_db.content = prompt_data.content
            if prompt_data.description is not None:
                prompt_db.description = prompt_data.description
            
            # Update folder
            if prompt_data.folder_path is not None:
                folder = session.query(FolderDB).filter_by(path=prompt_data.folder_path).first()
                if not folder and prompt_data.folder_path:
                    folder = self._create_folder_hierarchy(session, prompt_data.folder_path)
                prompt_db.folder_id = folder.id if folder else None
            
            # Update tags
            if prompt_data.tags is not None:
                prompt_db.tags.clear()
                for tag_name in prompt_data.tags:
                    tag = session.query(TagDB).filter_by(name=tag_name).first()
                    if not tag:
                        tag = TagDB(name=tag_name, category="custom")
                        session.add(tag)
                        session.flush()
                    prompt_db.tags.append(tag)
            
            session.commit()
            session.refresh(prompt_db)
            
            return self._prompt_db_to_pydantic(session, prompt_db)
    
    def delete_prompt(self, prompt_id: int) -> bool:
        """Delete a prompt."""
        with self.get_session() as session:
            prompt = session.query(PromptDB).filter_by(id=prompt_id).first()
            if not prompt:
                return False
            
            session.delete(prompt)
            session.commit()
            return True
    
    def search_prompts(self, search_params: PromptSearch) -> Tuple[List[Prompt], int]:
        """Search prompts with filtering and pagination."""
        with self.get_session() as session:
            query = session.query(PromptDB)
            
            # Text search
            if search_params.query:
                search_term = f"%{search_params.query}%"
                query = query.filter(
                    or_(
                        PromptDB.title.ilike(search_term),
                        PromptDB.content.ilike(search_term),
                        PromptDB.description.ilike(search_term)
                    )
                )
            
            # Folder filter
            if search_params.folder_path:
                folder = session.query(FolderDB).filter_by(path=search_params.folder_path).first()
                if folder:
                    query = query.filter_by(folder_id=folder.id)
                else:
                    return [], 0
            
            # Tag filter
            if search_params.tags:
                for tag_name in search_params.tags:
                    tag = session.query(TagDB).filter_by(name=tag_name).first()
                    if tag:
                        query = query.filter(PromptDB.tags.contains(tag))
            
            # Get total count
            total = query.count()
            
            # Apply pagination
            query = query.offset(search_params.offset).limit(search_params.limit)
            
            prompts_db = query.all()
            prompts = [self._prompt_db_to_pydantic(session, p) for p in prompts_db]
            
            return prompts, total
    
    def list_prompts(self, folder_path: Optional[str] = None, limit: int = 100, offset: int = 0) -> Tuple[List[Prompt], int]:
        """List prompts with optional folder filtering."""
        search_params = PromptSearch(folder_path=folder_path, limit=limit, offset=offset)
        return self.search_prompts(search_params)
    
    # Helper methods
    def _create_folder_hierarchy(self, session: Session, path: str) -> FolderDB:
        """Create folder hierarchy for a given path."""
        parts = [p for p in path.split('/') if p]
        current_path = ""
        parent_id = None
        
        for part in parts:
            current_path += f"/{part}"
            
            folder = session.query(FolderDB).filter_by(path=current_path).first()
            if not folder:
                folder = FolderDB(name=part, path=current_path, parent_id=parent_id)
                session.add(folder)
                session.flush()
            
            parent_id = folder.id
        
        return folder
    
    def _prompt_db_to_pydantic(self, session: Session, prompt_db: PromptDB) -> Prompt:
        """Convert SQLAlchemy prompt to Pydantic model."""
        folder_path = None
        if prompt_db.folder:
            folder_path = prompt_db.folder.path
        
        tags = [Tag.model_validate(tag) for tag in prompt_db.tags]
        
        return Prompt(
            id=prompt_db.id,
            title=prompt_db.title,
            content=prompt_db.content,
            description=prompt_db.description,
            folder_id=prompt_db.folder_id,
            folder_path=folder_path,
            created_at=prompt_db.created_at,
            updated_at=prompt_db.updated_at,
            tags=tags
        )
