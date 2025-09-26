"""
Stdio-based MCP server for Claude Desktop integration.

This implements the MCP protocol over stdin/stdout for direct Claude Desktop integration.
"""

import json
import sys
import asyncio
import logging
from typing import Dict, Any, Optional

from .database import Database
from .models import PromptSearch, PromptCreate, PromptUpdate


class MCPStdioServer:
    """MCP server that communicates via stdin/stdout for Claude Desktop."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize MCP stdio server."""
        self.db = Database(db_path)
        
        # Set up logging to stderr so it doesn't interfere with JSON communication
        logging.basicConfig(
            level=logging.ERROR,
            stream=sys.stderr,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    async def run(self):
        """Run the MCP server, reading from stdin and writing to stdout."""
        try:
            while True:
                line = sys.stdin.readline()
                if not line:
                    break
                
                try:
                    request = json.loads(line.strip())
                    response = await self.handle_request(request)
                    if response:
                        print(json.dumps(response), flush=True)
                except json.JSONDecodeError:
                    self.logger.error(f"Invalid JSON received: {line}")
                except Exception as e:
                    self.logger.error(f"Error handling request: {e}")
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": request.get("id") if 'request' in locals() else None,
                        "error": {
                            "code": -32603,
                            "message": "Internal error",
                            "data": str(e)
                        }
                    }
                    print(json.dumps(error_response), flush=True)
        except Exception as e:
            self.logger.error(f"Fatal error in MCP server: {e}")
    
    async def handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle incoming MCP request."""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        if method == "initialize":
            return await self.handle_initialize(request_id, params)
        elif method == "resources/list":
            return await self.handle_resources_list(request_id, params)
        elif method == "resources/read":
            return await self.handle_resources_read(request_id, params)
        elif method == "tools/list":
            return await self.handle_tools_list(request_id, params)
        elif method == "tools/call":
            return await self.handle_tools_call(request_id, params)
        elif method == "notifications/cancelled":
            # Handle cancellation notifications
            return None
        elif method == "notifications/initialized":
            # Handle initialization complete notification
            return None
        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
    
    async def handle_initialize(self, request_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request with version compatibility."""
        # Get client's requested protocol version
        client_protocol_version = params.get("protocolVersion", "2025-06-18")

        # Support both Claude (2025-06-18) and Perplexity (2024-11-05) versions
        supported_versions = ["2024-11-05", "2025-06-18"]

        # Use the client's requested version if supported, otherwise use latest
        protocol_version = client_protocol_version if client_protocol_version in supported_versions else "2025-06-18"

        self.logger.info(f"Client requested protocol version: {client_protocol_version}, using: {protocol_version}")

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": protocol_version,
                "capabilities": {
                    "resources": {"subscribe": True, "listChanged": False},
                    "tools": {}
                },
                "serverInfo": {
                    "name": "prompt-bookmarks",
                    "version": "0.1.0"
                }
            }
        }
    
    async def handle_resources_list(self, request_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resources/list request."""
        try:
            prompts, _ = self.db.list_prompts(limit=1000)
            resources = []
            
            for prompt in prompts:
                resources.append({
                    "uri": f"prompt:///{prompt.id}",
                    "name": prompt.title,
                    "description": prompt.description or f"Prompt: {prompt.content[:100]}...",
                    "mimeType": "text/plain"
                })
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"resources": resources}
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": "Internal error",
                    "data": str(e)
                }
            }
    
    async def handle_resources_read(self, request_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resources/read request."""
        try:
            uri = params.get("uri")
            if not uri or not uri.startswith("prompt:///"):
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32602,
                        "message": "Invalid URI"
                    }
                }
            
            prompt_id = int(uri.replace("prompt:///", ""))
            prompt = self.db.get_prompt(prompt_id)
            
            if not prompt:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32602,
                        "message": f"Prompt {prompt_id} not found"
                    }
                }
            
            # Format prompt content with metadata
            content = self._format_prompt_content(prompt)
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "contents": [{
                        "uri": uri,
                        "mimeType": "text/plain",
                        "text": content
                    }]
                }
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": "Internal error",
                    "data": str(e)
                }
            }
    
    async def handle_tools_list(self, request_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/list request."""
        tools = [
            {
                "name": "search_prompts",
                "description": "Search for prompts by query, tags, or folder",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "tags": {"type": "array", "items": {"type": "string"}, "description": "Filter by tags"},
                        "folder_path": {"type": "string", "description": "Filter by folder"},
                        "limit": {"type": "integer", "default": 10}
                    },
                    "additionalProperties": False
                }
            },
            {
                "name": "create_prompt",
                "description": "Create a new prompt",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Prompt title"},
                        "content": {"type": "string", "description": "Prompt content"},
                        "description": {"type": "string", "description": "Optional description"},
                        "folder_path": {"type": "string", "description": "Folder path"},
                        "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags"}
                    },
                    "required": ["title", "content"],
                    "additionalProperties": False
                }
            },
            {
                "name": "get_prompt",
                "description": "Get a prompt by ID for immediate use",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "prompt_id": {"type": "integer", "description": "Prompt ID"}
                    },
                    "required": ["prompt_id"],
                    "additionalProperties": False
                }
            },
            {
                "name": "use_prompt_template",
                "description": "Use a prompt template with variable substitution",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "prompt_id": {"type": "integer", "description": "Prompt ID"},
                        "variables": {"type": "object", "description": "Variables to substitute"}
                    },
                    "required": ["prompt_id"],
                    "additionalProperties": False
                }
            },
            {
                "name": "find_and_use_prompt",
                "description": "Search for and use a prompt with variables",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "variables": {"type": "object", "description": "Variables to substitute"}
                    },
                    "required": ["query"],
                    "additionalProperties": False
                }
            },
            {
                "name": "update_prompt",
                "description": "Update an existing prompt's title, content, description, folder, or tags",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "prompt_id": {"type": "integer", "description": "Prompt ID to update"},
                        "title": {"type": "string", "description": "New prompt title"},
                        "content": {"type": "string", "description": "New prompt content"},
                        "description": {"type": "string", "description": "New description"},
                        "folder_path": {"type": "string", "description": "New folder path"},
                        "tags": {"type": "array", "items": {"type": "string"}, "description": "New tags (replaces all existing tags)"}
                    },
                    "required": ["prompt_id"],
                    "additionalProperties": False
                }
            },
            {
                "name": "delete_prompt",
                "description": "Delete a prompt by ID",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "prompt_id": {"type": "integer", "description": "Prompt ID to delete"}
                    },
                    "required": ["prompt_id"],
                    "additionalProperties": False
                }
            },
            {
                "name": "get_folders",
                "description": "List all folders in the prompt library",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False
                }
            },
            {
                "name": "create_folder",
                "description": "Create a new folder path",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "folder_path": {"type": "string", "description": "Folder path to create (e.g., 'AI/Coding/Python')"}
                    },
                    "required": ["folder_path"],
                    "additionalProperties": False
                }
            },
            {
                "name": "delete_folder",
                "description": "Delete a folder and move its prompts to the parent folder",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "folder_path": {"type": "string", "description": "Folder path to delete (e.g., 'AI/Coding/Python')"}
                    },
                    "required": ["folder_path"],
                    "additionalProperties": False
                }
            },
            {
                "name": "update_folder",
                "description": "Rename a folder (updates the folder path and all child folders/prompts)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "old_path": {"type": "string", "description": "Current folder path (e.g., 'AI/Coding')"},
                        "new_path": {"type": "string", "description": "New folder path (e.g., 'AI/Development')"}
                    },
                    "required": ["old_path", "new_path"],
                    "additionalProperties": False
                }
            },
            {
                "name": "get_tags",
                "description": "List all tags in the prompt library",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False
                }
            },
            {
                "name": "create_tag",
                "description": "Create a new tag",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Tag name"},
                        "category": {"type": "string", "description": "Tag category (optional)"},
                        "color": {"type": "string", "description": "Hex color code (optional, e.g., '#FF5733')"}
                    },
                    "required": ["name"],
                    "additionalProperties": False
                }
            },
            {
                "name": "update_tag",
                "description": "Update an existing tag's name, category, or color",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "current_name": {"type": "string", "description": "Current tag name"},
                        "new_name": {"type": "string", "description": "New tag name (optional)"},
                        "category": {"type": "string", "description": "New category (optional)"},
                        "color": {"type": "string", "description": "New hex color code (optional, e.g., '#FF5733')"}
                    },
                    "required": ["current_name"],
                    "additionalProperties": False
                }
            },
            {
                "name": "delete_tag",
                "description": "Delete a tag by name",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Tag name to delete"}
                    },
                    "required": ["name"],
                    "additionalProperties": False
                }
            }
        ]
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"tools": tools}
        }
    
    async def handle_tools_call(self, request_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request."""
        try:
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            if tool_name == "search_prompts":
                result = await self._search_prompts_tool(arguments)
            elif tool_name == "create_prompt":
                result = await self._create_prompt_tool(arguments)
            elif tool_name == "get_prompt":
                result = await self._get_prompt_tool(arguments)
            elif tool_name == "use_prompt_template":
                result = await self._use_prompt_template_tool(arguments)
            elif tool_name == "find_and_use_prompt":
                result = await self._find_and_use_prompt_tool(arguments)
            elif tool_name == "update_prompt":
                result = await self._update_prompt_tool(arguments)
            elif tool_name == "delete_prompt":
                result = await self._delete_prompt_tool(arguments)
            elif tool_name == "get_folders":
                result = await self._get_folders_tool(arguments)
            elif tool_name == "create_folder":
                result = await self._create_folder_tool(arguments)
            elif tool_name == "delete_folder":
                result = await self._delete_folder_tool(arguments)
            elif tool_name == "update_folder":
                result = await self._update_folder_tool(arguments)
            elif tool_name == "get_tags":
                result = await self._get_tags_tool(arguments)
            elif tool_name == "create_tag":
                result = await self._create_tag_tool(arguments)
            elif tool_name == "update_tag":
                result = await self._update_tag_tool(arguments)
            elif tool_name == "delete_tag":
                result = await self._delete_tag_tool(arguments)
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Unknown tool: {tool_name}"
                    }
                }
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{
                        "type": "text",
                        "text": json.dumps(result, indent=2)
                    }]
                }
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": "Internal error",
                    "data": str(e)
                }
            }
    
    async def _search_prompts_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search prompts tool implementation."""
        search_params = PromptSearch(
            query=arguments.get("query"),
            tags=arguments.get("tags", []),
            folder_path=arguments.get("folder_path"),
            limit=arguments.get("limit", 10)
        )
        
        prompts, total = self.db.search_prompts(search_params)
        
        results = []
        for prompt in prompts:
            results.append({
                "id": prompt.id,
                "title": prompt.title,
                "content": prompt.content,
                "description": prompt.description,
                "folder_path": prompt.folder_path,
                "tags": [tag.name for tag in prompt.tags],
                "created_at": prompt.created_at.isoformat() if prompt.created_at else None
            })
        
        return {
            "prompts": results,
            "total": total,
            "count": len(results)
        }
    
    async def _create_prompt_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Create prompt tool implementation."""
        prompt_data = PromptCreate(
            title=arguments.get("title"),
            content=arguments.get("content"),
            description=arguments.get("description"),
            folder_path=arguments.get("folder_path"),
            tags=arguments.get("tags", [])
        )
        
        prompt = self.db.create_prompt(prompt_data)
        
        return {
            "success": True,
            "prompt": {
                "id": prompt.id,
                "title": prompt.title,
                "content": prompt.content,
                "description": prompt.description,
                "folder_path": prompt.folder_path,
                "tags": [tag.name for tag in prompt.tags]
            }
        }
    
    async def _get_prompt_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get prompt tool implementation."""
        prompt_id = arguments.get("prompt_id")
        if not prompt_id:
            raise ValueError("prompt_id is required")
        
        prompt = self.db.get_prompt(prompt_id)
        
        if not prompt:
            return {"error": f"Prompt with ID {prompt_id} not found"}
        
        return {
            "prompt_content": prompt.content,
            "title": prompt.title,
            "description": prompt.description,
            "tags": [tag.name for tag in prompt.tags],
            "folder_path": prompt.folder_path
        }
    
    async def _use_prompt_template_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Use prompt template tool implementation."""
        prompt_id = arguments.get("prompt_id")
        variables = arguments.get("variables", {})
        
        if not prompt_id:
            raise ValueError("prompt_id is required")
        
        prompt = self.db.get_prompt(prompt_id)
        
        if not prompt:
            return {"error": f"Prompt with ID {prompt_id} not found"}
        
        # Substitute variables in the prompt content
        content = prompt.content
        for key, value in variables.items():
            content = content.replace(f"{{{key}}}", str(value))
            content = content.replace(f"{{{{{key}}}}}", str(value))
        
        return {
            "prompt_content": content,
            "original_content": prompt.content,
            "title": prompt.title,
            "variables_used": variables,
            "description": prompt.description,
            "tags": [tag.name for tag in prompt.tags],
            "folder_path": prompt.folder_path
        }
    
    async def _find_and_use_prompt_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Find and use prompt tool implementation."""
        query = arguments.get("query")
        variables = arguments.get("variables", {})
        
        if not query:
            raise ValueError("query is required")
        
        # Search for prompts
        search_params = PromptSearch(query=query, limit=5)
        prompts, total = self.db.search_prompts(search_params)
        
        if not prompts:
            return {"error": f"No prompts found matching '{query}'"}
        
        # Use the first/best match
        best_prompt = prompts[0]
        
        # Substitute variables if provided
        content = best_prompt.content
        for key, value in variables.items():
            content = content.replace(f"{{{key}}}", str(value))
            content = content.replace(f"{{{{{key}}}}}", str(value))
        
        return {
            "prompt_content": content,
            "original_content": best_prompt.content if variables else None,
            "prompt_id": best_prompt.id,
            "title": best_prompt.title,
            "description": best_prompt.description,
            "tags": [tag.name for tag in best_prompt.tags],
            "folder_path": best_prompt.folder_path,
            "variables_used": variables if variables else None,
            "search_results_count": total
        }
    
    async def _update_prompt_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Update prompt tool implementation."""
        prompt_id = arguments.get("prompt_id")
        if not prompt_id:
            raise ValueError("prompt_id is required")
        
        # Get current prompt
        current_prompt = self.db.get_prompt(prompt_id)
        if not current_prompt:
            return {"error": f"Prompt with ID {prompt_id} not found"}
        
        # Prepare update data - only include fields that are provided
        from .models import PromptUpdate
        update_data = {"id": prompt_id}
        
        if "title" in arguments:
            update_data["title"] = arguments["title"]
        if "content" in arguments:
            update_data["content"] = arguments["content"] 
        if "description" in arguments:
            update_data["description"] = arguments["description"]
        if "folder_path" in arguments:
            update_data["folder_path"] = arguments["folder_path"]
        if "tags" in arguments:
            update_data["tags"] = arguments["tags"]
        
        prompt_update = PromptUpdate(**update_data)
        updated_prompt = self.db.update_prompt(prompt_id, prompt_update)
        
        return {
            "success": True,
            "prompt": {
                "id": updated_prompt.id,
                "title": updated_prompt.title,
                "content": updated_prompt.content,
                "description": updated_prompt.description,
                "folder_path": updated_prompt.folder_path,
                "tags": [tag.name for tag in updated_prompt.tags]
            }
        }
    
    async def _delete_prompt_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Delete prompt tool implementation."""
        prompt_id = arguments.get("prompt_id")
        if not prompt_id:
            raise ValueError("prompt_id is required")
        
        # Check if prompt exists
        prompt = self.db.get_prompt(prompt_id)
        if not prompt:
            return {"error": f"Prompt with ID {prompt_id} not found"}
        
        # Delete the prompt
        self.db.delete_prompt(prompt_id)
        
        return {
            "success": True,
            "message": f"Deleted prompt '{prompt.title}' (ID: {prompt_id})"
        }
    
    async def _get_folders_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get folders tool implementation."""
        folders = self.db.list_folders()
        
        return {
            "folders": [
                {
                    "path": folder.path,
                    "prompt_count": folder.prompt_count,
                    "created_at": folder.created_at.isoformat() if folder.created_at else None
                }
                for folder in folders
            ],
            "count": len(folders)
        }
    
    async def _create_folder_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Create folder tool implementation."""
        folder_path = arguments.get("folder_path")
        if not folder_path:
            raise ValueError("folder_path is required")
        
        # Create folder by creating a dummy prompt and then deleting it
        # This ensures the folder structure exists
        from .models import PromptCreate
        temp_prompt = PromptCreate(
            title="__temp__",
            content="temp",
            folder_path=folder_path
        )
        created_prompt = self.db.create_prompt(temp_prompt)
        self.db.delete_prompt(created_prompt.id)
        
        return {
            "success": True,
            "folder_path": folder_path,
            "message": f"Created folder path '{folder_path}'"
        }
    
    async def _delete_folder_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Delete folder tool implementation."""
        folder_path = arguments.get("folder_path")
        if not folder_path:
            raise ValueError("folder_path is required")
        
        # Ensure folder_path starts with /
        if not folder_path.startswith("/"):
            folder_path = "/" + folder_path
        
        # Check if folder exists and get info before deletion
        folders = self.db.list_folders()
        target_folder = None
        for folder in folders:
            if folder.path == folder_path:
                target_folder = folder
                break
        
        if not target_folder:
            return {"error": f"Folder '{folder_path}' not found"}
        
        # Check if it's the root folder
        if folder_path == "/":
            return {"error": "Cannot delete the root folder"}
        
        # Delete the folder
        success = self.db.delete_folder(folder_path)
        
        if success:
            return {
                "success": True,
                "folder_path": folder_path,
                "message": f"Deleted folder '{folder_path}' and moved {target_folder.prompt_count} prompts to parent folder"
            }
        else:
            return {"error": f"Failed to delete folder '{folder_path}'"}
    
    async def _update_folder_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Update folder tool implementation - rename a folder and update all child paths."""
        old_path = arguments.get("old_path")
        new_path = arguments.get("new_path")
        
        if not old_path or not new_path:
            raise ValueError("Both old_path and new_path are required")
        
        # Ensure paths start with /
        if not old_path.startswith("/"):
            old_path = "/" + old_path
        if not new_path.startswith("/"):
            new_path = "/" + new_path
        
        # Check if old folder exists
        folders = self.db.list_folders()
        old_folder = None
        for folder in folders:
            if folder.path == old_path:
                old_folder = folder
                break
        
        if not old_folder:
            return {"error": f"Folder '{old_path}' not found"}
        
        # Check if new path already exists
        for folder in folders:
            if folder.path == new_path:
                return {"error": f"Folder '{new_path}' already exists"}
        
        # Check if it's the root folder
        if old_path == "/":
            return {"error": "Cannot rename the root folder"}
        
        # Check if new_path would be a child of old_path (which would cause issues)
        if new_path.startswith(old_path + "/"):
            return {"error": f"Cannot move folder to be a child of itself"}
        
        try:
            # Get all folders that need to be updated (old folder and its children)
            folders_to_update = []
            for folder in folders:
                if folder.path == old_path or folder.path.startswith(old_path + "/"):
                    folders_to_update.append(folder)
            
            # Get all prompts that need to be updated
            prompts_to_update = []
            # Search for prompts in the old folder and its children
            from .models import PromptSearch
            
            # Get prompts directly in the old folder
            search_params = PromptSearch(folder_path=old_path, limit=1000)
            prompts_in_folder, _ = self.db.search_prompts(search_params)
            prompts_to_update.extend(prompts_in_folder)
            
            # Get prompts in child folders by searching for each child folder
            for folder in folders_to_update:
                if folder.path != old_path:  # Skip the main folder, already got those
                    search_params = PromptSearch(folder_path=folder.path, limit=1000)
                    child_prompts, _ = self.db.search_prompts(search_params)
                    prompts_to_update.extend(child_prompts)
            
            # Create the new folder structure
            for folder in folders_to_update:
                # Calculate new path for this folder
                if folder.path == old_path:
                    folder_new_path = new_path
                else:
                    # Replace the old_path prefix with new_path
                    folder_new_path = new_path + folder.path[len(old_path):]
                
                # Create the new folder (this will create parent hierarchy if needed)
                self._create_folder_if_not_exists(folder_new_path)
            
            # Update all prompts to use new folder paths
            from .models import PromptUpdate
            for prompt in prompts_to_update:
                if prompt.folder_path == old_path:
                    prompt_new_path = new_path
                else:
                    prompt_new_path = new_path + prompt.folder_path[len(old_path):]
                
                prompt_update = PromptUpdate(
                    id=prompt.id,
                    folder_path=prompt_new_path
                )
                self.db.update_prompt(prompt.id, prompt_update)
            
            # Delete old folder structure (in reverse order to handle children first)
            folders_to_update.sort(key=lambda f: f.path.count('/'), reverse=True)
            for folder in folders_to_update:
                self.db.delete_folder(folder.path)
            
            return {
                "success": True,
                "old_path": old_path,
                "new_path": new_path,
                "folders_updated": len(folders_to_update),
                "prompts_updated": len(prompts_to_update),
                "message": f"Renamed folder '{old_path}' to '{new_path}' and updated {len(folders_to_update)} folders and {len(prompts_to_update)} prompts"
            }
            
        except Exception as e:
            return {"error": f"Failed to rename folder: {str(e)}"}
    
    def _create_folder_if_not_exists(self, folder_path: str):
        """Helper method to create a folder if it doesn't exist."""
        existing_folders = self.db.list_folders()
        for folder in existing_folders:
            if folder.path == folder_path:
                return  # Folder already exists
        
        # Create folder by creating a temp prompt and deleting it
        from .models import PromptCreate
        temp_prompt = PromptCreate(
            title="__temp_for_folder__",
            content="temp",
            folder_path=folder_path
        )
        created_prompt = self.db.create_prompt(temp_prompt)
        self.db.delete_prompt(created_prompt.id)
    
    async def _get_tags_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get tags tool implementation."""
        tags = self.db.list_tags()
        
        return {
            "tags": [
                {
                    "id": tag.id,
                    "name": tag.name,
                    "category": tag.category,
                    "color": tag.color,
                    "created_at": tag.created_at.isoformat() if tag.created_at else None
                }
                for tag in tags
            ],
            "count": len(tags)
        }
    
    async def _create_tag_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Create tag tool implementation."""
        name = arguments.get("name")
        if not name:
            raise ValueError("name is required")
        
        # Check if tag already exists
        existing_tag = self.db.get_tag_by_name(name)
        if existing_tag:
            return {
                "success": True,
                "tag": {
                    "id": existing_tag.id,
                    "name": existing_tag.name,
                    "category": existing_tag.category,
                    "color": existing_tag.color
                },
                "message": f"Tag '{name}' already exists"
            }
        
        created_tag = self.db.create_tag(
            name=name,
            category=arguments.get("category"),
            color=arguments.get("color")
        )
        
        return {
            "success": True,
            "tag": {
                "id": created_tag.id,
                "name": created_tag.name,
                "category": created_tag.category,
                "color": created_tag.color
            },
            "message": f"Created tag '{name}'"
        }
    
    async def _update_tag_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Update tag tool implementation."""
        current_name = arguments.get("current_name")
        if not current_name:
            raise ValueError("current_name is required")
        
        # Check if tag exists
        existing_tag = self.db.get_tag_by_name(current_name)
        if not existing_tag:
            return {"error": f"Tag '{current_name}' not found"}
        
        # Get new values (use existing if not provided)
        new_name = arguments.get("new_name", existing_tag.name)
        new_category = arguments.get("category", existing_tag.category)
        new_color = arguments.get("color", existing_tag.color)
        
        # Check if new name conflicts with existing tag (if name is changing)
        if new_name != current_name:
            name_conflict = self.db.get_tag_by_name(new_name)
            if name_conflict:
                return {"error": f"Tag '{new_name}' already exists"}
        
        try:
            # Delete old tag and create new one (since there's no update method)
            self.db.delete_tag(current_name)
            updated_tag = self.db.create_tag(
                name=new_name,
                category=new_category,
                color=new_color
            )
            
            return {
                "success": True,
                "tag": {
                    "id": updated_tag.id,
                    "name": updated_tag.name,
                    "category": updated_tag.category,
                    "color": updated_tag.color
                },
                "old_name": current_name,
                "message": f"Updated tag '{current_name}' to '{new_name}'" if new_name != current_name else f"Updated tag '{current_name}'"
            }
            
        except Exception as e:
            return {"error": f"Failed to update tag: {str(e)}"}
    
    async def _delete_tag_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Delete tag tool implementation."""
        name = arguments.get("name")
        if not name:
            raise ValueError("name is required")
        
        # Check if tag exists
        existing_tag = self.db.get_tag_by_name(name)
        if not existing_tag:
            return {"error": f"Tag '{name}' not found"}
        
        # Delete the tag
        success = self.db.delete_tag(name)
        
        if success:
            return {
                "success": True,
                "tag_name": name,
                "message": f"Deleted tag '{name}'"
            }
        else:
            return {"error": f"Failed to delete tag '{name}'"}
    
    def _format_prompt_content(self, prompt) -> str:
        """Format prompt content with metadata for display."""
        lines = [f"# {prompt.title}", ""]
        
        if prompt.description:
            lines.extend([f"**Description:** {prompt.description}", ""])
        
        if prompt.folder_path:
            lines.extend([f"**Folder:** {prompt.folder_path}", ""])
        
        if prompt.tags:
            tag_names = [tag.name for tag in prompt.tags]
            lines.extend([f"**Tags:** {', '.join(tag_names)}", ""])
        
        lines.extend(["---", "", prompt.content])
        
        return "\n".join(lines)


def main():
    """Main entry point for stdio MCP server."""
    import sys
    from pathlib import Path
    
    # Default database path
    data_dir = Path.home() / ".prompt_bookmarks"
    data_dir.mkdir(exist_ok=True)
    db_path = str(data_dir / "prompts.db")
    
    # Create and run server
    server = MCPStdioServer(db_path)
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
