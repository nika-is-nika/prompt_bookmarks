# Prompt Bookmarks MCP Extension

A Model Context Protocol (MCP) server that helps you store, organize and manage prompts with hierarchical folders, tags, and variable substitution.

## Installation

1. Download the `prompt-bookmarks.dxt` file
2. In Claude Desktop, go to Settings → Extensions
3. Click "Install Extension" and select the `prompt-bookmarks.dxt` file
4. The extension will automatically install dependencies and set up the database

## Features

- **Hierarchical Organization**: Organize prompts in nested folders
- **Tag System**: Categorize prompts with flexible tagging
- **Variable Substitution**: Use templates with placeholder variables
- **Search & Filter**: Find prompts by content, tags, or folder
- **Full CRUD Operations**: Create, read, update, and delete prompts
- **Persistent Storage**: Local SQLite database for your prompts

## Usage

Once installed, the extension provides these MCP tools:

- `search_prompts` - Search for prompts by content, tags, or folder
- `create_prompt` - Create new prompts with content, tags, and folder organization
- `get_prompt` - Retrieve a specific prompt by ID
- `update_prompt` - Update existing prompt content, metadata, or organization
- `delete_prompt` - Remove prompts from the system
- `use_prompt_template` - Use prompts with variable substitution
- `find_and_use_prompt` - Search and immediately use prompts with variables
- `get_folders` - List all folder structures
- `create_folder` - Create new folder hierarchies
- `update_folder` - Rename folders and update child paths
- `delete_folder` - Remove folders and reorganize content
- `get_tags` - List all available tags
- `create_tag` - Create new tags with categories and colors
- `update_tag` - Update tag properties
- `delete_tag` - Remove tags from the system

## Requirements

- Python 3.8+
- Dependencies are automatically installed during setup

## License

MIT License - See LICENSE file for details.

## Support

For issues and feature requests, visit: https://github.com/veronikatamaioflores/prompt_bookmarks
