# Prompt Bookmarks

A tool for organizing and accessing prompts across AI tools via Model Context Protocol (MCP).

## Features

- **Hierarchical Organization** - Organize prompts in folders and subfolders
- **Flexible Tagging** - Tag prompts by topic, tool, or custom categories
- **Claude Desktop Integration** - Direct stdio-based MCP integration for seamless access
- **Template Variables** - Use prompts with variable substitution like `{name}` or `{{project}}`
- **Multi-Tool Support** - Works with Claude Desktop, Perplexity, and other MCP-compatible AI tools
- **Shared Database** - Single prompt library accessible across all connected AI tools
- **CLI Interface** - Command-line management for all operations
- **Search & Filter** - Find prompts quickly by content, tags, or folders
- **Real-time Updates** - Changes sync instantly between CLI and MCP interfaces
- **Minimal Dependencies** - Clean architecture with only essential packages

## Installation

### 🚀 DXT Package (Claude Desktop)

**For Claude Desktop users:**

1. Download `prompt-bookmarks.dxt` from releases
2. Open Claude Desktop and navigate to Settings -> Extensions.
3. Drag the dxt file to Claude Desktop.
4. Click Install and then enable the Extension with a toggle.
5. The extension automatically installs Python dependencies
6. Enjoy! ✨

### 🔌 Manual MCP Setup (Perplexity)

**For Perplexity or other MCP-compatible tools:**

1. Clone or download this repository to your local machine.
2. Install Python dependencies:

   ```bash
   cd prompt_bookmarks
   python -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   pip install -r requirements.txt
   python install.py
   ```

3. Navigate to Connectors in settings and add new conenctor with the following:

   ```json
   {
     "args": ["/path/to/prompt_bookmarks/index.js"],
     "command": "node",
     "env": {},
     "useBuiltInNode": true
   }
   ```

4. Replace `/path/to/prompt_bookmarks` with your actual installation path.
5. Give the connector a name.
6. Click Save.
7. Enjoy! ✨

### ⚙️ Development Installation

1. **Install**:

   ```bash
   pip install -e .
   ```

2. **Initialize**:

   ```bash
   prompt-bookmarks init
   ```

3. **Add a prompt**:

   ```bash
   prompt-bookmarks add "My prompt" --folder "dev" --tags "python,debugging"
   ```

4. **Configure your AI tool**:

   ```json
   {
     "mcpServers": {
       "prompt-bookmarks": {
         "command": "/path/to/your/prompt_bookmarks/venv/bin/prompt-bookmarks",
         "args": ["serve"],
         "env": {}
       }
     }
   }
   ```

   **Find your path**:

   ```bash
   cd /path/to/your/prompt_bookmarks
   source venv/bin/activate
   which prompt-bookmarks
   ```

5. **Restart Claude Desktop** completely and test with:
   > *"What MCP tools do you have available?"*

## Usage

### CLI Commands

- `init` - Initialize the prompt database
- `add` - Add a new prompt
- `list` - List prompts with filtering
- `search` - Search prompts by content
- `edit` - Edit an existing prompt
- `delete` - Delete a prompt
- `serve` - Start MCP server for Claude Desktop integration

### MCP Integration

Once configured, you can manage prompts directly from Claude Desktop conversations:

**Example usage:**

- *"Create a prompt titled 'Code Review' with content 'Please review this {language} code for {aspects}' in folder 'Development' with tags 'coding' and 'review'"*
- *"Search my prompts for 'python' and show me the top 5"*
- *"Find and use a prompt about code review with variables language='JavaScript' and aspects='performance'"*
- *"Update prompt ID 3 to change its folder to 'AI/Templates'"*
- *"Show me all my folders and create a new one called 'Personal/Notes'"*

**Available MCP Tools (15 total):**

**Prompt Management:**

- `search_prompts` - Find prompts by content, tags, or folder (supports limit parameter)
- `create_prompt` - Save new prompts during conversations
- `get_prompt` - Retrieve prompt content for immediate use
- `update_prompt` - Modify existing prompts (title, content, description, folder, tags)
- `delete_prompt` - Remove outdated prompts
- `use_prompt_template` - Use prompts with variable substitution
- `find_and_use_prompt` - Search and immediately use prompts with variables

**Organization:**

- `get_folders` - List all folder structures
- `create_folder` - Create new folder paths (e.g., 'AI/Coding/Python')
- `update_folder` - Rename folders and update all child folders/prompts
- `delete_folder` - Remove folders and move prompts to parent
- `get_tags` - List all available tags
- `create_tag` - Create tags with categories and colors
- `update_tag` - Update tag name, category, or color
- `delete_tag` - Remove tags from the system

## Variable Substitution

Prompts support dynamic variables in two formats:

- `{variable_name}` - Single braces
- `{{variable_name}}` - Double braces

**Example:**

```bash
Hello {name},

Thank you for your interest in {product}.

Best regards,
{sender}
```

**Usage:** *"Use prompt ID 5 with variables name='John', product='our software', sender='Sarah'"*

## Advanced Usage Examples

**Creating & Organizing:**

- *"Create a prompt called 'Bug Report Template' with content 'Bug: {title}\nSteps: {steps}\nExpected: {expected}\nActual: {actual}' in folder 'Templates' with tags 'bug' and 'template'"*
- *"Create a folder 'AI/Writing/Blog' and a tag 'content-creation' with category 'workflow' and color '#00D4AA'"*

**Managing Structure:**

- *"Rename folder 'AI/Coding' to 'AI/Development' to better reflect its purpose"*
- *"Update tag 'old-name' to 'new-name' and change its category to 'productivity'"*
- *"Update prompt ID 5 to change the title to 'Enhanced Code Review' and add tag 'quality-assurance'"*

**Using Templates:**

- *"Find a prompt about code review and use it with language='Python' and focus='security'"*
- *"Search my prompts for 'python' with limit 25"*

**Batch Operations:**

- *"First, create a prompt for meeting notes with variables {date}, {attendees}, {topics}. Then search for all prompts tagged 'meetings' and show me the first 3."*

## Organization Features

**Hierarchical Folders:**

- `AI/Coding/Python`
- `Marketing/Email/Welcome`  
- `Templates/Reports`

**Flexible Tagging:**

- **AI Tools**: `claude`, `chatgpt`, `perplexity`
- **Topics**: `coding`, `writing`, `analysis`
- **Categories**: `template`, `example`, `draft`
- **Custom**: Any tag with optional category and color

## Troubleshooting

**Tools Not Available:**

1. Verify path: `which prompt-bookmarks`
2. Restart Claude Desktop after config changes
3. Check config file syntax (JSON must be valid)
4. For MCPB installation issues, check Claude Desktop logs for "spawn python ENOENT" errors

**Server Issues:**

1. Ensure virtual environment is activated
2. Test command: `prompt-bookmarks --help`
3. Make executable: `chmod +x /path/to/venv/bin/prompt-bookmarks`

**Limits:**

- Prompts: Up to 1,000 per search (default: 10)
- Folders: No limit (returns all)
- Tags: No limit (returns all)

## Tips for Best Results

1. **Be specific** in search queries for better results
2. **Use consistent tagging** for easier organization  
3. **Create templates** with variables for reusable prompts
4. **Organize with folders** to maintain logical structure
5. **Test variables** to ensure proper substitution

## Development

1. Clone and set up:

   ```bash
   git clone <repo>
   cd prompt_bookmarks
   python -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   pip install -e ".[dev]"
   ```

2. Run tests:

   ```bash
   pytest
   ```

## Requirements

- **Python 3.8+** (automatically managed in DXT package)
- **Node.js 16+** (for DXT package execution)
- **Dependencies** are automatically installed during setup

## Support

For issues and feature requests, visit: <https://github.com/veronikatamaioflores/prompt_bookmarks>

## License

MIT License - see LICENSE file for details.
