#!/usr/bin/env python3
"""
Wrapper script to run the Prompt Bookmarks MCP server.
This script ensures the package is properly set up and runs the server.
"""
import sys
import os
import asyncio
from pathlib import Path

def main():
    # Get the directory where this script is located
    script_dir = Path(__file__).parent.absolute()

    # Add the src directory to Python path
    src_dir = script_dir / "src"
    if src_dir.exists():
        sys.path.insert(0, str(src_dir))

    try:
        # Try to import and run the server
        from prompt_bookmarks.mcp_server import MCPStdioServer
        from prompt_bookmarks.database import Database

        # Initialize database if needed
        db_path = Path.home() / ".prompt_bookmarks" / "prompts.db"
        db_path.parent.mkdir(exist_ok=True)

        if not db_path.exists():
            # Initialize the database
            db = Database(str(db_path))
            db.init_db()

        # Run the MCP server
        server = MCPStdioServer(str(db_path))
        asyncio.run(server.run())

    except ImportError as e:
        print(f"Error importing prompt_bookmarks: {e}", file=sys.stderr)
        print("Make sure the package is properly installed.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error running server: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()