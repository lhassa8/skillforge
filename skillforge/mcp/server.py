"""MCP Server generation and management.

Generate and run MCP servers that expose SkillForge skills as tools.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

from skillforge.skill import Skill, SkillParseError
from skillforge.mcp.mapping import (
    MCPToolDefinition,
    skill_to_mcp_tool,
)


class MCPServerError(Exception):
    """Raised when MCP server operations fail."""
    pass


# Server configuration file name
SERVER_CONFIG_FILE = "mcp-server.yml"
TOOLS_DIR = "tools"


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server.

    Stored as mcp-server.yml in the server directory.
    """
    name: str
    description: str = ""
    version: str = "1.0.0"
    host: str = "localhost"
    port: int = 8080
    tools: list[str] = field(default_factory=list)  # Tool names

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "server": {
                "host": self.host,
                "port": self.port,
            },
            "tools": self.tools,
        }

    @classmethod
    def from_dict(cls, data: dict) -> MCPServerConfig:
        """Create from dictionary."""
        server_data = data.get("server", {})
        return cls(
            name=data.get("name", "mcp-server"),
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            host=server_data.get("host", "localhost"),
            port=server_data.get("port", 8080),
            tools=data.get("tools", []),
        )

    def save(self, server_dir: Path) -> None:
        """Save configuration to disk."""
        config_path = server_dir / SERVER_CONFIG_FILE
        content = yaml.dump(
            self.to_dict(),
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )
        config_path.write_text(content)

    @classmethod
    def load(cls, server_dir: Path) -> MCPServerConfig:
        """Load configuration from disk."""
        config_path = server_dir / SERVER_CONFIG_FILE

        if not config_path.exists():
            raise MCPServerError(f"Server config not found: {config_path}")

        content = config_path.read_text()
        data = yaml.safe_load(content)

        if not isinstance(data, dict):
            raise MCPServerError(f"Invalid server config format: {config_path}")

        return cls.from_dict(data)


@dataclass
class MCPServerProject:
    """An MCP server project directory.

    Structure:
        my-server/
        ├── mcp-server.yml     # Server configuration
        ├── tools/             # Tool definitions
        │   ├── tool-name.json
        │   └── ...
        └── server.py          # Generated server script
    """
    path: Path
    config: MCPServerConfig
    tools: dict[str, MCPToolDefinition] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        server_dir: Path,
        name: Optional[str] = None,
        description: str = "",
        port: int = 8080,
    ) -> MCPServerProject:
        """Create a new MCP server project.

        Args:
            server_dir: Directory for the server project
            name: Server name (defaults to directory name)
            description: Server description
            port: Port to run server on

        Returns:
            MCPServerProject instance

        Raises:
            MCPServerError: If directory already exists
        """
        server_dir = Path(server_dir)

        if server_dir.exists():
            raise MCPServerError(f"Directory already exists: {server_dir}")

        # Create directory structure
        server_dir.mkdir(parents=True)
        (server_dir / TOOLS_DIR).mkdir()

        # Create config
        config = MCPServerConfig(
            name=name or server_dir.name,
            description=description,
            port=port,
        )
        config.save(server_dir)

        # Generate server script
        project = cls(path=server_dir, config=config)
        project._generate_server_script()

        return project

    @classmethod
    def load(cls, server_dir: Path) -> MCPServerProject:
        """Load an existing MCP server project.

        Args:
            server_dir: Path to server directory

        Returns:
            MCPServerProject instance

        Raises:
            MCPServerError: If not a valid server project
        """
        server_dir = Path(server_dir)

        if not server_dir.exists():
            raise MCPServerError(f"Server directory not found: {server_dir}")

        config = MCPServerConfig.load(server_dir)

        # Load tools
        tools = {}
        tools_dir = server_dir / TOOLS_DIR
        if tools_dir.exists():
            for tool_file in tools_dir.glob("*.json"):
                try:
                    data = json.loads(tool_file.read_text())
                    tool = MCPToolDefinition.from_dict(data)
                    tools[tool.name] = tool
                except (json.JSONDecodeError, KeyError) as e:
                    raise MCPServerError(f"Invalid tool file {tool_file}: {e}")

        return cls(path=server_dir, config=config, tools=tools)

    def add_skill(self, skill_path: Path) -> MCPToolDefinition:
        """Add a skill to the server.

        Args:
            skill_path: Path to skill directory

        Returns:
            The created tool definition

        Raises:
            MCPServerError: If skill cannot be loaded
        """
        try:
            skill = Skill.from_directory(skill_path)
        except SkillParseError as e:
            raise MCPServerError(f"Cannot load skill: {e}")

        # Convert to MCP tool
        tool = skill_to_mcp_tool(skill)

        # Save tool definition
        tool_path = self.path / TOOLS_DIR / f"{tool.name}.json"
        tool_path.write_text(json.dumps(tool.to_dict(), indent=2))

        # Update config
        if tool.name not in self.config.tools:
            self.config.tools.append(tool.name)
            self.config.save(self.path)

        self.tools[tool.name] = tool

        # Regenerate server script
        self._generate_server_script()

        return tool

    def remove_tool(self, tool_name: str) -> bool:
        """Remove a tool from the server.

        Args:
            tool_name: Name of tool to remove

        Returns:
            True if removed, False if not found
        """
        if tool_name not in self.tools:
            return False

        # Remove tool file
        tool_path = self.path / TOOLS_DIR / f"{tool_name}.json"
        if tool_path.exists():
            tool_path.unlink()

        # Update config
        if tool_name in self.config.tools:
            self.config.tools.remove(tool_name)
            self.config.save(self.path)

        del self.tools[tool_name]

        # Regenerate server script
        self._generate_server_script()

        return True

    def list_tools(self) -> list[MCPToolDefinition]:
        """List all tools in the server."""
        return list(self.tools.values())

    def _generate_server_script(self) -> None:
        """Generate the Python server script."""
        script_path = self.path / "server.py"

        # Generate tool definitions as Python code
        tools_code = []
        for tool in self.tools.values():
            tool_schema = tool.to_mcp_schema()
            tools_code.append(f"    {json.dumps(tool_schema, indent=4)},")

        tools_list = "\n".join(tools_code) if tools_code else ""

        # Generate tool handlers
        handlers_code = []
        for tool in self.tools.values():
            handler = f'''
    elif name == "{tool.name}":
        # Skill: {tool.name}
        # {tool.description}
        request = arguments.get("request", "")
        skill_content = SKILL_CONTENT.get("{tool.name}", "")
        return [
            types.TextContent(
                type="text",
                text=f"[Skill: {tool.name}]\\n\\nUser request: {{request}}\\n\\nSkill instructions:\\n{{skill_content}}"
            )
        ]'''
            handlers_code.append(handler)

        handlers = "\n".join(handlers_code) if handlers_code else ""

        # Generate skill content dictionary
        skill_content_items = []
        for tool in self.tools.values():
            escaped_content = tool.skill_content.replace('"""', '\\"\\"\\"')
            skill_content_items.append(f'    "{tool.name}": """{escaped_content}""",')

        skill_content_dict = "\n".join(skill_content_items)

        script_content = f'''#!/usr/bin/env python3
"""MCP Server: {self.config.name}

{self.config.description}

Generated by SkillForge. Do not edit directly.
Regenerate with: skillforge mcp add <server> <skill>
"""

import asyncio
import json
from typing import Any

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp import types
except ImportError:
    print("Error: MCP package not installed.")
    print("Install with: pip install mcp")
    exit(1)


# Skill content for each tool
SKILL_CONTENT = {{
{skill_content_dict}
}}

# Tool definitions
TOOLS = [
{tools_list}
]

# Create server
server = Server("{self.config.name}")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """Return list of available tools."""
    return [types.Tool(**t) for t in TOOLS]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    """Handle tool calls."""
    if False:
        pass  # Placeholder for tool handlers
{handlers}
    else:
        return [
            types.TextContent(
                type="text",
                text=f"Unknown tool: {{name}}"
            )
        ]


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
'''

        script_path.write_text(script_content)
        # Make executable
        script_path.chmod(0o755)

    def get_mcp_config(self) -> dict:
        """Get MCP client configuration for this server.

        Returns a configuration snippet that can be added to
        Claude Desktop or other MCP clients.
        """
        return {
            self.config.name: {
                "command": sys.executable,
                "args": [str(self.path / "server.py")],
            }
        }


def init_server(
    server_dir: Path,
    name: Optional[str] = None,
    description: str = "",
    port: int = 8080,
) -> MCPServerProject:
    """Initialize a new MCP server project.

    Args:
        server_dir: Directory for the server
        name: Server name
        description: Server description
        port: Port number

    Returns:
        MCPServerProject instance
    """
    return MCPServerProject.create(
        server_dir=server_dir,
        name=name,
        description=description,
        port=port,
    )


def load_server(server_dir: Path) -> MCPServerProject:
    """Load an existing MCP server project.

    Args:
        server_dir: Path to server directory

    Returns:
        MCPServerProject instance
    """
    return MCPServerProject.load(server_dir)


def add_skill_to_server(server_dir: Path, skill_path: Path) -> MCPToolDefinition:
    """Add a skill to an MCP server.

    Args:
        server_dir: Path to server directory
        skill_path: Path to skill directory

    Returns:
        The created tool definition
    """
    project = MCPServerProject.load(server_dir)
    return project.add_skill(skill_path)


def remove_tool_from_server(server_dir: Path, tool_name: str) -> bool:
    """Remove a tool from an MCP server.

    Args:
        server_dir: Path to server directory
        tool_name: Name of tool to remove

    Returns:
        True if removed, False if not found
    """
    project = MCPServerProject.load(server_dir)
    return project.remove_tool(tool_name)


def list_server_tools(server_dir: Path) -> list[MCPToolDefinition]:
    """List tools in an MCP server.

    Args:
        server_dir: Path to server directory

    Returns:
        List of tool definitions
    """
    project = MCPServerProject.load(server_dir)
    return project.list_tools()


def run_server(server_dir: Path) -> subprocess.Popen:
    """Run an MCP server.

    Args:
        server_dir: Path to server directory

    Returns:
        Subprocess running the server
    """
    server_dir = Path(server_dir)
    script_path = server_dir / "server.py"

    if not script_path.exists():
        raise MCPServerError(f"Server script not found: {script_path}")

    return subprocess.Popen(
        [sys.executable, str(script_path)],
        cwd=str(server_dir),
    )


def is_mcp_server(path: Path) -> bool:
    """Check if a path is an MCP server project.

    Args:
        path: Path to check

    Returns:
        True if path is a valid MCP server project
    """
    path = Path(path)
    return path.is_dir() and (path / SERVER_CONFIG_FILE).exists()
