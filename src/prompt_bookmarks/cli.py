"""
Command-line interface for Prompt Bookmarks.

Provides commands for managing prompts, folders, and tags.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import List, Optional
import click
from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from rich.syntax import Syntax

from .database import Database
from .models import PromptCreate, PromptUpdate, PromptSearch
from .mcp_server import MCPStdioServer


console = Console()


def get_default_db_path() -> str:
    """Get default database path."""
    data_dir = Path.home() / ".prompt_bookmarks"
    data_dir.mkdir(exist_ok=True)
    return str(data_dir / "prompts.db")


@click.group()
@click.option('--db-path', '-d', help='Database path', default=get_default_db_path())
@click.pass_context
def cli(ctx, db_path: str):
    """Prompt Bookmarks - Organize and access your prompts across AI tools."""
    ctx.ensure_object(dict)
    ctx.obj['db_path'] = db_path
    ctx.obj['db'] = Database(db_path)


@cli.command()
@click.pass_context
def init(ctx):
    """Initialize the prompt database."""
    db_path = ctx.obj['db_path']
    
    if os.path.exists(db_path):
        if not click.confirm(f"Database already exists at {db_path}. Reinitialize?"):
            return
    
    # Initialize database (this happens automatically in Database.__init__)
    db = Database(db_path)
    
    console.print(f"Initialized prompt database at: {db_path}", style="green")
    console.print("\nDefault folders and tags have been created.")
    console.print("\nGet started:")
    console.print("  • Add a prompt: prompt-bookmarks add \"Your prompt here\"")
    console.print("  • List prompts: prompt-bookmarks list")
    console.print("  • Start MCP server: prompt-bookmarks serve")


@cli.command()
@click.argument('title')
@click.argument('content')
@click.option('--description', '-desc', help='Prompt description')
@click.option('--folder', '-f', help='Folder path (e.g., "AI/Coding")')
@click.option('--tags', '-t', multiple=True, help='Tags (can be used multiple times)')
@click.pass_context
def add(ctx, title: str, content: str, description: Optional[str], folder: Optional[str], tags: List[str]):
    """Add a new prompt."""
    db = ctx.obj['db']
    
    try:
        prompt_data = PromptCreate(
            title=title,
            content=content,
            description=description,
            folder_path=folder,
            tags=list(tags)
        )
        
        prompt = db.create_prompt(prompt_data)
        
        console.print(f"Created prompt: {prompt.title}", style="green")
        console.print(f"Folder: {prompt.folder_path or 'Root'}")
        if prompt.tags:
            console.print(f"Tags: {', '.join([tag.name for tag in prompt.tags])}")
        console.print(f"ID: {prompt.id}")
        
    except Exception as e:
        console.print(f"Error creating prompt: {e}", style="red")


@cli.command('list')
@click.option('--folder', '-f', help='Filter by folder path')
@click.option('--tag', '-t', multiple=True, help='Filter by tags')
@click.option('--limit', '-l', default=20, help='Maximum number of results')
@click.option('--verbose', '-v', is_flag=True, help='Show full content')
@click.pass_context
def list_prompts(ctx, folder: Optional[str], tag: List[str], limit: int, verbose: bool):
    """List prompts with optional filtering."""
    db = ctx.obj['db']
    
    try:
        search_params = PromptSearch(
            folder_path=folder,
            tags=list(tag) if tag else None,
            limit=limit
        )
        
        prompts, total = db.search_prompts(search_params)
        
        if not prompts:
            console.print("No prompts found.", style="yellow")
            return
        
        # Create table
        table = Table(title=f"Prompts ({len(prompts)}/{total})")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Title", style="white", no_wrap=True)
        table.add_column("Folder", style="blue")
        table.add_column("Tags", style="green")
        
        if verbose:
            table.add_column("Content", style="dim")
        
        for prompt in prompts:
            folder_display = prompt.folder_path or "/"
            tags_display = ", ".join([tag.name for tag in prompt.tags]) if prompt.tags else ""
            
            row = [
                str(prompt.id),
                prompt.title,
                folder_display,
                tags_display
            ]
            
            if verbose:
                content_preview = prompt.content[:100] + "..." if len(prompt.content) > 100 else prompt.content
                row.append(content_preview)
            
            table.add_row(*row)
        
        console.print(table)
        
    except Exception as e:
        console.print(f"Error listing prompts: {e}", style="red")


@cli.command()
@click.argument('query')
@click.option('--folder', '-f', help='Filter by folder path')
@click.option('--tag', '-t', multiple=True, help='Filter by tags')
@click.option('--limit', '-l', default=10, help='Maximum number of results')
@click.pass_context
def search(ctx, query: str, folder: Optional[str], tag: List[str], limit: int):
    """Search prompts by content."""
    db = ctx.obj['db']
    
    try:
        search_params = PromptSearch(
            query=query,
            folder_path=folder,
            tags=list(tag) if tag else None,
            limit=limit
        )
        
        prompts, total = db.search_prompts(search_params)
        
        if not prompts:
            console.print(f"No prompts found matching '{query}'", style="yellow")
            return
        
        console.print(f"Found {len(prompts)}/{total} prompts matching '{query}':")
        
        for prompt in prompts:
            panel_content = []
            
            if prompt.description:
                panel_content.append(f"[dim]{prompt.description}[/dim]")
                panel_content.append("")
            
            # Show content preview
            content_lines = prompt.content.split('\n')
            if len(content_lines) > 3:
                content_preview = '\n'.join(content_lines[:3]) + "\n[dim]...[/dim]"
            else:
                content_preview = prompt.content
            
            panel_content.append(content_preview)
            panel_content.append("")
            
            # Metadata
            metadata = []
            if prompt.folder_path:
                metadata.append(f"Folder: {prompt.folder_path}")
            if prompt.tags:
                metadata.append(f"Tags: {', '.join([tag.name for tag in prompt.tags])}")
            metadata.append(f"ID: {prompt.id}")
            
            panel_content.append(" • ".join(metadata))
            
            panel = Panel(
                "\n".join(panel_content),
                title=f"[bold]{prompt.title}[/bold]",
                border_style="blue"
            )
            console.print(panel)
            console.print()
        
    except Exception as e:
        console.print(f" Error searching prompts: {e}", style="red")


@cli.command()
@click.argument('prompt_id', type=int)
@click.pass_context
def show(ctx, prompt_id: int):
    """Show full prompt details."""
    db = ctx.obj['db']
    
    try:
        prompt = db.get_prompt(prompt_id)
        
        if not prompt:
            console.print(f" Prompt {prompt_id} not found", style="red")
            return
        
        # Title
        console.print(f"\n[bold cyan]# {prompt.title}[/bold cyan]")
        
        # Metadata
        if prompt.description:
            console.print(f"\n[dim]{prompt.description}[/dim]")
        
        metadata = []
        if prompt.folder_path:
            metadata.append(f" Folder: {prompt.folder_path}")
        if prompt.tags:
            metadata.append(f"  Tags: {', '.join([tag.name for tag in prompt.tags])}")
        metadata.append(f" ID: {prompt.id}")
        metadata.append(f"📅 Created: {prompt.created_at.strftime('%Y-%m-%d %H:%M') if prompt.created_at else 'Unknown'}")
        
        console.print("\n" + " • ".join(metadata))
        
        # Content
        console.print("\n" + "─" * 50)
        syntax = Syntax(prompt.content, "text", theme="monokai", line_numbers=False)
        console.print(syntax)
        console.print("─" * 50)
        
    except Exception as e:
        console.print(f" Error showing prompt: {e}", style="red")


@cli.command()
@click.argument('prompt_id', type=int)
@click.option('--title', help='New title')
@click.option('--content', help='New content')
@click.option('--description', help='New description')
@click.option('--folder', help='New folder path')
@click.option('--tags', help='New tags (comma-separated)')
@click.pass_context
def edit(ctx, prompt_id: int, title: Optional[str], content: Optional[str], 
         description: Optional[str], folder: Optional[str], tags: Optional[str]):
    """Edit an existing prompt."""
    db = ctx.obj['db']
    
    try:
        # Check if prompt exists
        existing = db.get_prompt(prompt_id)
        if not existing:
            console.print(f" Prompt {prompt_id} not found", style="red")
            return
        
        # Parse tags
        tag_list = None
        if tags is not None:
            tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
        
        # Create update data
        update_data = PromptUpdate(
            title=title,
            content=content,
            description=description,
            folder_path=folder,
            tags=tag_list
        )
        
        # Update prompt
        updated_prompt = db.update_prompt(prompt_id, update_data)
        
        if updated_prompt:
            console.print(f" Updated prompt: {updated_prompt.title}", style="green")
        else:
            console.print(f" Failed to update prompt {prompt_id}", style="red")
        
    except Exception as e:
        console.print(f" Error updating prompt: {e}", style="red")


@cli.command()
@click.argument('prompt_id', type=int)
@click.confirmation_option(prompt='Are you sure you want to delete this prompt?')
@click.pass_context
def delete(ctx, prompt_id: int):
    """Delete a prompt."""
    db = ctx.obj['db']
    
    try:
        # Check if prompt exists
        existing = db.get_prompt(prompt_id)
        if not existing:
            console.print(f" Prompt {prompt_id} not found", style="red")
            return
        
        # Delete prompt
        success = db.delete_prompt(prompt_id)
        
        if success:
            console.print(f" Deleted prompt: {existing.title}", style="green")
        else:
            console.print(f" Failed to delete prompt {prompt_id}", style="red")
        
    except Exception as e:
        console.print(f" Error deleting prompt: {e}", style="red")


@cli.command()
@click.option('--category', help='Filter by category')
@click.pass_context
def tags(ctx, category: Optional[str]):
    """List all tags."""
    db = ctx.obj['db']
    
    try:
        tags = db.list_tags(category)
        
        if not tags:
            console.print("  No tags found.", style="yellow")
            return
        
        # Group by category
        categories = {}
        for tag in tags:
            cat = tag.category or "uncategorized"
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(tag)
        
        for cat, cat_tags in categories.items():
            console.print(f"\n[bold]{cat.title()}[/bold]")
            for tag in cat_tags:
                color_indicator = f"[{tag.color}]●[/]" if tag.color else "○"
                console.print(f"  {color_indicator} {tag.name}")
        
    except Exception as e:
        console.print(f" Error listing tags: {e}", style="red")


@cli.command()
@click.option('--parent', help='Parent folder path')
@click.pass_context
def folders(ctx, parent: Optional[str]):
    """List folders."""
    db = ctx.obj['db']
    
    try:
        folders = db.list_folders(parent)
        
        if not folders:
            console.print(" No folders found.", style="yellow")
            return
        
        table = Table(title="Folders")
        table.add_column("Name", style="cyan")
        table.add_column("Path", style="blue")
        table.add_column("Prompts", style="green")
        
        for folder in folders:
            table.add_row(folder.name, folder.path, str(folder.prompt_count))
        
        console.print(table)
        
    except Exception as e:
        console.print(f" Error listing folders: {e}", style="red")


@cli.command()
@click.pass_context
def serve(ctx):
    """Start MCP server for Claude Desktop integration."""
    import asyncio
    
    db_path = ctx.obj['db_path']
    
    # Create and run stdio MCP server
    server = MCPStdioServer(db_path)
    asyncio.run(server.run())


@cli.command()
@click.argument('file', type=click.Path(exists=True))
@click.option('--folder', help='Import into specific folder')
@click.pass_context
def import_prompts(ctx, file: str, folder: Optional[str]):
    """Import prompts from JSON file."""
    db = ctx.obj['db']
    
    try:
        with open(file, 'r') as f:
            data = json.load(f)
        
        imported = 0
        for item in data:
            try:
                prompt_data = PromptCreate(
                    title=item['title'],
                    content=item['content'],
                    description=item.get('description'),
                    folder_path=folder or item.get('folder_path'),
                    tags=item.get('tags', [])
                )
                
                db.create_prompt(prompt_data)
                imported += 1
                
            except Exception as e:
                console.print(f"  Skipped invalid prompt: {e}", style="yellow")
        
        console.print(f" Imported {imported} prompts from {file}", style="green")
        
    except Exception as e:
        console.print(f" Error importing prompts: {e}", style="red")


def main():
    """Main CLI entry point."""
    cli()
