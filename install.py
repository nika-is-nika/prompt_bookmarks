#!/usr/bin/env python3
"""
Installation script for Prompt Bookmarks MCP server.
Handles dependency installation automatically.
"""
import subprocess
import sys
import os
from pathlib import Path

def install_dependencies():
    """Install required Python packages."""
    requirements = [
        "click>=8.0.0",
        "sqlalchemy>=2.0.0",
        "pydantic>=2.0.0",
        "rich>=13.0.0",
        "python-dotenv>=1.0.0",
        "pyyaml>=6.0"
    ]

    print("Installing Prompt Bookmarks dependencies...")
    try:
        for req in requirements:
            print(f"Installing {req}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", req])
        print("✅ All dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing dependencies: {e}")
        return False

def setup_database():
    """Initialize the database if it doesn't exist."""
    try:
        # Add src to path
        script_dir = Path(__file__).parent.absolute()
        src_dir = script_dir / "src"
        sys.path.insert(0, str(src_dir))

        from prompt_bookmarks.database import Database

        # Setup database
        db_path = Path.home() / ".prompt_bookmarks" / "prompts.db"
        db_path.parent.mkdir(exist_ok=True)

        if not db_path.exists():
            print("Setting up database...")
            db = Database(str(db_path))
            db.init_db()
            print("✅ Database initialized!")
        else:
            print("✅ Database already exists.")

        return True
    except Exception as e:
        print(f"❌ Error setting up database: {e}")
        return False

def main():
    print("🚀 Setting up Prompt Bookmarks MCP Server...")

    # Install dependencies
    if not install_dependencies():
        sys.exit(1)

    # Setup database
    if not setup_database():
        sys.exit(1)

    print("\n✅ Installation complete! You can now use the Prompt Bookmarks MCP server.")
    print("The server will be available as 'prompt-bookmarks' in Claude Desktop.")

if __name__ == "__main__":
    main()