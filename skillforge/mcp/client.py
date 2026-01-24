"""MCP Client for discovering and importing tools from MCP servers.

This module provides functionality to:
- Connect to MCP servers
- List available tools
- Import MCP tools as SkillForge skills
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from skillforge.mcp.mapping import (
    MCPToolDefinition,
    MCPMappingError,
    mcp_tool_to_skill,
    parse_mcp_tool_response,
)


class MCPClientError(Exception):
    """Raised when MCP client operations fail."""
    pass


@dataclass
class MCPServerInfo:
    """Information about an MCP server."""
    name: str
    command: str
    args: list[str]
    env: dict[str, str]

    @classmethod
    def from_config(cls, name: str, config: dict) -> MCPServerInfo:
        """Create from MCP client config entry."""
        return cls(
            name=name,
            command=config.get("command", ""),
            args=config.get("args", []),
            env=config.get("env", {}),
        )


@dataclass
class DiscoveredTool:
    """A tool discovered from an MCP server."""
    name: str
    description: str
    server_name: str
    tool_definition: MCPToolDefinition


def discover_tools_from_config(
    config_path: Path,
    server_name: Optional[str] = None,
) -> list[DiscoveredTool]:
    """Discover tools from MCP servers defined in a config file.

    Args:
        config_path: Path to MCP client config (e.g., claude_desktop_config.json)
        server_name: Optional specific server to query

    Returns:
        List of discovered tools

    Raises:
        MCPClientError: If config cannot be read or servers fail
    """
    config_path = Path(config_path)

    if not config_path.exists():
        raise MCPClientError(f"Config file not found: {config_path}")

    try:
        config = json.loads(config_path.read_text())
    except json.JSONDecodeError as e:
        raise MCPClientError(f"Invalid JSON in config: {e}")

    mcp_servers = config.get("mcpServers", {})
    if not mcp_servers:
        return []

    tools = []
    for name, server_config in mcp_servers.items():
        if server_name and name != server_name:
            continue

        try:
            server_info = MCPServerInfo.from_config(name, server_config)
            server_tools = _query_server_tools(server_info)
            tools.extend(server_tools)
        except MCPClientError:
            # Skip servers that fail to respond
            continue

    return tools


def discover_tools_from_server(
    command: str,
    args: Optional[list[str]] = None,
    server_name: str = "unknown",
) -> list[DiscoveredTool]:
    """Discover tools from an MCP server by running it.

    Args:
        command: Command to run the server
        args: Arguments for the command
        server_name: Name to identify the server

    Returns:
        List of discovered tools
    """
    server_info = MCPServerInfo(
        name=server_name,
        command=command,
        args=args or [],
        env={},
    )
    return _query_server_tools(server_info)


def _query_server_tools(server_info: MCPServerInfo) -> list[DiscoveredTool]:
    """Query an MCP server for its tools.

    Uses stdio transport to communicate with the server.
    """
    # Build command
    cmd = [server_info.command] + server_info.args

    # MCP initialization request
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "skillforge",
                "version": "0.10.0",
            },
        },
    }

    # List tools request
    list_tools_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {},
    }

    try:
        # Start server process
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**dict(__import__("os").environ), **server_info.env},
        )

        # Send initialization
        init_msg = json.dumps(init_request) + "\n"
        process.stdin.write(init_msg.encode())
        process.stdin.flush()

        # Read initialization response
        init_response = process.stdout.readline()
        if not init_response:
            raise MCPClientError("Server did not respond to initialization")

        # Send initialized notification
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
        }
        process.stdin.write((json.dumps(initialized_notification) + "\n").encode())
        process.stdin.flush()

        # Send list tools request
        list_msg = json.dumps(list_tools_request) + "\n"
        process.stdin.write(list_msg.encode())
        process.stdin.flush()

        # Read response
        response_line = process.stdout.readline()
        process.terminate()

        if not response_line:
            raise MCPClientError("Server did not respond to tools/list")

        response = json.loads(response_line)

        if "error" in response:
            raise MCPClientError(f"Server error: {response['error']}")

        result = response.get("result", {})
        tool_list = result.get("tools", [])

        tools = []
        for tool_data in tool_list:
            try:
                tool_def = parse_mcp_tool_response(tool_data)
                tools.append(DiscoveredTool(
                    name=tool_def.name,
                    description=tool_def.description,
                    server_name=server_info.name,
                    tool_definition=tool_def,
                ))
            except MCPMappingError:
                continue

        return tools

    except FileNotFoundError:
        raise MCPClientError(f"Server command not found: {server_info.command}")
    except subprocess.TimeoutExpired:
        raise MCPClientError("Server did not respond in time")
    except json.JSONDecodeError as e:
        raise MCPClientError(f"Invalid JSON from server: {e}")


def import_tool_as_skill(
    tool: DiscoveredTool,
    output_dir: Path,
) -> Path:
    """Import an MCP tool as a SkillForge skill.

    Args:
        tool: The discovered tool to import
        output_dir: Directory to save the skill

    Returns:
        Path to the created skill directory

    Raises:
        MCPClientError: If import fails
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Convert to skill
    skill = mcp_tool_to_skill(tool.tool_definition)

    # Create skill directory
    skill_dir = output_dir / skill.name
    if skill_dir.exists():
        raise MCPClientError(f"Skill directory already exists: {skill_dir}")

    skill_dir.mkdir()

    # Write SKILL.md
    skill_md_path = skill_dir / "SKILL.md"
    skill_md_path.write_text(skill.to_skill_md())

    return skill_dir


def import_tool_by_name(
    tool_name: str,
    config_path: Path,
    output_dir: Path,
    server_name: Optional[str] = None,
) -> Path:
    """Import an MCP tool by name from configured servers.

    Args:
        tool_name: Name of the tool to import
        config_path: Path to MCP client config
        output_dir: Directory to save the skill
        server_name: Optional specific server to search

    Returns:
        Path to the created skill directory

    Raises:
        MCPClientError: If tool not found or import fails
    """
    tools = discover_tools_from_config(config_path, server_name)

    for tool in tools:
        if tool.name == tool_name:
            return import_tool_as_skill(tool, output_dir)

    raise MCPClientError(f"Tool '{tool_name}' not found in any configured server")


def get_claude_desktop_config_path() -> Optional[Path]:
    """Get the path to Claude Desktop's MCP config file.

    Returns:
        Path to config file, or None if not found
    """
    import platform

    system = platform.system()

    if system == "Darwin":  # macOS
        config_path = Path.home() / "Library/Application Support/Claude/claude_desktop_config.json"
    elif system == "Windows":
        config_path = Path.home() / "AppData/Roaming/Claude/claude_desktop_config.json"
    elif system == "Linux":
        config_path = Path.home() / ".config/Claude/claude_desktop_config.json"
    else:
        return None

    return config_path if config_path.exists() else None


def list_configured_servers(config_path: Optional[Path] = None) -> list[MCPServerInfo]:
    """List MCP servers from config file.

    Args:
        config_path: Path to config, or None to use Claude Desktop config

    Returns:
        List of server info
    """
    if config_path is None:
        config_path = get_claude_desktop_config_path()

    if config_path is None or not config_path.exists():
        return []

    try:
        config = json.loads(config_path.read_text())
    except (json.JSONDecodeError, OSError):
        return []

    mcp_servers = config.get("mcpServers", {})

    return [
        MCPServerInfo.from_config(name, server_config)
        for name, server_config in mcp_servers.items()
    ]
