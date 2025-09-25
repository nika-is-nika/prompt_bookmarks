"""
Data models for Prompt Bookmarks.

Defines the core data structures for prompts, folders, and tags.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

# Association table for many-to-many relationship between prompts and tags
prompt_tags = Table(
    'prompt_tags',
    Base.metadata,
    Column('prompt_id', Integer, ForeignKey('prompts.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id'), primary_key=True)
)


class PromptDB(Base):
    """SQLAlchemy model for prompts."""
    __tablename__ = 'prompts'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    description = Column(Text)
    folder_id = Column(Integer, ForeignKey('folders.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    folder = relationship("FolderDB", back_populates="prompts")
    tags = relationship("TagDB", secondary=prompt_tags, back_populates="prompts")


class FolderDB(Base):
    """SQLAlchemy model for folders."""
    __tablename__ = 'folders'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    path = Column(String(500), nullable=False, unique=True)  # Full path like "AI/Coding/Python"
    parent_id = Column(Integer, ForeignKey('folders.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    parent = relationship("FolderDB", remote_side=[id], back_populates="children")
    children = relationship("FolderDB", back_populates="parent")
    prompts = relationship("PromptDB", back_populates="folder")


class TagDB(Base):
    """SQLAlchemy model for tags."""
    __tablename__ = 'tags'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False, unique=True)
    category = Column(String(50))  # e.g., "ai_tool", "topic", "custom"
    color = Column(String(7))  # Hex color code
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    prompts = relationship("PromptDB", secondary=prompt_tags, back_populates="tags")


# Pydantic models for API and validation
class Tag(BaseModel):
    """Pydantic model for tags."""
    id: Optional[int] = None
    name: str = Field(..., min_length=1, max_length=50)
    category: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class Folder(BaseModel):
    """Pydantic model for folders."""
    id: Optional[int] = None
    name: str = Field(..., min_length=1, max_length=100)
    path: str = Field(..., min_length=1, max_length=500)
    parent_id: Optional[int] = None
    created_at: Optional[datetime] = None
    children: List['Folder'] = []
    prompt_count: int = 0
    
    class Config:
        from_attributes = True


class Prompt(BaseModel):
    """Pydantic model for prompts."""
    id: Optional[int] = None
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    description: Optional[str] = None
    folder_id: Optional[int] = None
    folder_path: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    tags: List[Tag] = []
    
    class Config:
        from_attributes = True


class PromptCreate(BaseModel):
    """Model for creating new prompts."""
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    description: Optional[str] = None
    folder_path: Optional[str] = None
    tags: List[str] = []


class PromptUpdate(BaseModel):
    """Model for updating prompts."""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = None
    folder_path: Optional[str] = None
    tags: Optional[List[str]] = None


class PromptSearch(BaseModel):
    """Model for search parameters."""
    query: Optional[str] = None
    folder_path: Optional[str] = None
    tags: Optional[List[str]] = None
    limit: int = Field(100, ge=1, le=1000)
    offset: int = Field(0, ge=0)


class MCPPromptResource(BaseModel):
    """MCP resource representation of a prompt."""
    uri: str
    name: str
    description: str
    mime_type: str = "text/plain"
    
    @classmethod
    def from_prompt(cls, prompt: Prompt) -> 'MCPPromptResource':
        """Create MCP resource from prompt."""
        return cls(
            uri=f"prompt:///{prompt.id}",
            name=prompt.title,
            description=prompt.description or prompt.content[:100] + "..." if len(prompt.content) > 100 else prompt.content,
            mime_type="text/plain"
        )


# Forward reference resolution
Folder.model_rebuild()
