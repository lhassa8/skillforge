"""MCP (Model Context Protocol) integration for SkillForge.

This module provides bidirectional integration between SkillForge skills
and MCP servers:

- Convert skills to MCP tools
- Generate MCP servers from skills
- Import MCP tools as skills

Example usage:

    from skillforge.mcp import (
        # Mapping
        skill_to_mcp_tool,
        mcp_tool_to_skill,
        MCPToolDefinition,

        # Server
        init_server,
        add_skill_to_server,
        run_server,

        # Client
        discover_tools_from_config,
        import_tool_as_skill,
    )

    # Create an MCP server from skills
    project = init_server("./my-server", name="my-skills")
    project.add_skill("./skills/code-reviewer")

    # Convert a skill to MCP tool
    skill = Skill.from_directory("./skills/my-skill")
    tool = skill_to_mcp_tool(skill)

    # Discover tools from MCP servers
    tools = discover_tools_from_config("~/.config/claude_desktop_config.json")
    for tool in tools:
        print(f"Found: {tool.name} from {tool.server_name}")
"""

from skillforge.mcp.mapping import (
    MCPMappingError,
    MCPToolDefinition,
    MCPToolParameter,
    mcp_tool_to_skill,
    parse_mcp_tool_response,
    skill_to_mcp_tool,
    validate_tool_name,
)

from skillforge.mcp.server import (
    MCPServerConfig,
    MCPServerError,
    MCPServerProject,
    SERVER_CONFIG_FILE,
    add_skill_to_server,
    init_server,
    is_mcp_server,
    list_server_tools,
    load_server,
    remove_tool_from_server,
    run_server,
)

from skillforge.mcp.client import (
    DiscoveredTool,
    MCPClientError,
    MCPServerInfo,
    discover_tools_from_config,
    discover_tools_from_server,
    get_claude_desktop_config_path,
    import_tool_as_skill,
    import_tool_by_name,
    list_configured_servers,
)

__all__ = [
    # Mapping
    "MCPMappingError",
    "MCPToolDefinition",
    "MCPToolParameter",
    "mcp_tool_to_skill",
    "parse_mcp_tool_response",
    "skill_to_mcp_tool",
    "validate_tool_name",
    # Server
    "MCPServerConfig",
    "MCPServerError",
    "MCPServerProject",
    "SERVER_CONFIG_FILE",
    "add_skill_to_server",
    "init_server",
    "is_mcp_server",
    "list_server_tools",
    "load_server",
    "remove_tool_from_server",
    "run_server",
    # Client
    "DiscoveredTool",
    "MCPClientError",
    "MCPServerInfo",
    "discover_tools_from_config",
    "discover_tools_from_server",
    "get_claude_desktop_config_path",
    "import_tool_as_skill",
    "import_tool_by_name",
    "list_configured_servers",
]
