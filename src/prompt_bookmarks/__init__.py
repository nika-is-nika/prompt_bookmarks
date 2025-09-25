"""
Prompt Bookmarks - A tool for organizing and accessing prompts across AI tools.

This package provides:
- Hierarchical prompt organization with folders and tags
- Local MCP server for AI tool integration
- CLI interface for prompt management
- Import/export functionality
"""

__version__ = "0.1.0"
__author__ = "Nika Tamaio Flores"
__email__ = "tamayoflores.n@gmail.com"

from .models import Prompt, Folder, Tag
from .database import Database
from .mcp_server import MCPStdioServer

__all__ = ["Prompt", "Folder", "Tag", "Database", "MCPStdioServer"]
