"""Tests for MCP (Model Context Protocol) integration."""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from skillforge.mcp import (
    # Mapping
    MCPMappingError,
    MCPToolDefinition,
    MCPToolParameter,
    mcp_tool_to_skill,
    parse_mcp_tool_response,
    skill_to_mcp_tool,
    validate_tool_name,
    # Server
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
    # Client
    DiscoveredTool,
    MCPClientError,
    MCPServerInfo,
    discover_tools_from_config,
    get_claude_desktop_config_path,
    import_tool_as_skill,
    list_configured_servers,
)
from skillforge.skill import Skill


# =============================================================================
# MCPToolParameter Tests
# =============================================================================

class TestMCPToolParameter:
    """Tests for MCPToolParameter dataclass."""

    def test_basic_parameter(self):
        """Test creating a basic parameter."""
        param = MCPToolParameter(
            name="input",
            description="The input text",
        )
        assert param.name == "input"
        assert param.description == "The input text"
        assert param.type == "string"
        assert param.required is False

    def test_to_json_schema(self):
        """Test converting parameter to JSON Schema."""
        param = MCPToolParameter(
            name="count",
            description="Number of items",
            type="integer",
            default=10,
        )
        schema = param.to_json_schema()

        assert schema["type"] == "integer"
        assert schema["description"] == "Number of items"
        assert schema["default"] == 10

    def test_enum_parameter(self):
        """Test parameter with enum values."""
        param = MCPToolParameter(
            name="format",
            description="Output format",
            enum=["json", "yaml", "text"],
        )
        schema = param.to_json_schema()

        assert schema["enum"] == ["json", "yaml", "text"]


# =============================================================================
# MCPToolDefinition Tests
# =============================================================================

class TestMCPToolDefinition:
    """Tests for MCPToolDefinition dataclass."""

    def test_basic_tool(self):
        """Test creating a basic tool definition."""
        tool = MCPToolDefinition(
            name="my-tool",
            description="A test tool",
        )
        assert tool.name == "my-tool"
        assert tool.description == "A test tool"
        assert tool.parameters == []

    def test_to_mcp_schema(self):
        """Test converting to MCP schema format."""
        tool = MCPToolDefinition(
            name="code-review",
            description="Review code for issues",
            parameters=[
                MCPToolParameter(
                    name="code",
                    description="Code to review",
                    required=True,
                ),
                MCPToolParameter(
                    name="language",
                    description="Programming language",
                    required=False,
                ),
            ],
        )
        schema = tool.to_mcp_schema()

        assert schema["name"] == "code-review"
        assert schema["description"] == "Review code for issues"
        assert schema["inputSchema"]["type"] == "object"
        assert "code" in schema["inputSchema"]["properties"]
        assert "language" in schema["inputSchema"]["properties"]
        assert "code" in schema["inputSchema"]["required"]
        assert "language" not in schema["inputSchema"]["required"]

    def test_to_dict_and_from_dict(self):
        """Test serialization round-trip."""
        original = MCPToolDefinition(
            name="test-tool",
            description="Test description",
            parameters=[
                MCPToolParameter(
                    name="param1",
                    description="First param",
                    type="string",
                    required=True,
                ),
            ],
            skill_content="# Instructions\nDo something",
            version="1.0.0",
        )

        data = original.to_dict()
        restored = MCPToolDefinition.from_dict(data)

        assert restored.name == original.name
        assert restored.description == original.description
        assert restored.version == original.version
        assert restored.skill_content == original.skill_content
        assert len(restored.parameters) == len(original.parameters)
        assert restored.parameters[0].name == original.parameters[0].name


# =============================================================================
# Mapping Functions Tests
# =============================================================================

class TestSkillToMCPTool:
    """Tests for skill_to_mcp_tool function."""

    def test_basic_skill_conversion(self):
        """Test converting a basic skill to MCP tool."""
        skill = Skill(
            name="code-reviewer",
            description="Review code for issues",
            content="# Code Review Instructions\n\nReview the provided code.",
        )
        tool = skill_to_mcp_tool(skill)

        assert tool.name == "code-reviewer"
        assert tool.description == "Review code for issues"
        assert tool.skill_content == skill.content
        # Should have default "request" parameter
        assert len(tool.parameters) == 1
        assert tool.parameters[0].name == "request"

    def test_skill_with_parameters_section(self):
        """Test extracting parameters from skill content."""
        skill = Skill(
            name="formatter",
            description="Format text",
            content="""# Formatter

## Parameters

- `text` (string): The text to format (required)
- `style`: The formatting style
- `indent` (integer): Indentation level

## Instructions

Format the text according to the style.
""",
        )
        tool = skill_to_mcp_tool(skill)

        assert len(tool.parameters) == 3
        param_names = [p.name for p in tool.parameters]
        assert "text" in param_names
        assert "style" in param_names
        assert "indent" in param_names

    def test_skill_with_version(self):
        """Test that version is preserved."""
        skill = Skill(
            name="versioned-skill",
            description="A versioned skill",
            content="Instructions",
            version="2.1.0",
        )
        tool = skill_to_mcp_tool(skill)

        assert tool.version == "2.1.0"


class TestMCPToolToSkill:
    """Tests for mcp_tool_to_skill function."""

    def test_basic_tool_conversion(self):
        """Test converting MCP tool to skill."""
        tool = MCPToolDefinition(
            name="file-reader",
            description="Read files from disk",
            parameters=[
                MCPToolParameter(
                    name="path",
                    description="File path to read",
                    required=True,
                ),
            ],
        )
        skill = mcp_tool_to_skill(tool)

        assert skill.name == "file-reader"
        assert skill.description == "Read files from disk"
        assert "## Parameters" in skill.content
        assert "`path`" in skill.content

    def test_tool_with_skill_content(self):
        """Test preserving original skill content."""
        tool = MCPToolDefinition(
            name="custom-tool",
            description="Custom tool",
            skill_content="# Original instructions\n\nDo something specific.",
        )
        skill = mcp_tool_to_skill(tool)

        assert "## Instructions" in skill.content
        assert "Original instructions" in skill.content


class TestParseMCPToolResponse:
    """Tests for parse_mcp_tool_response function."""

    def test_parse_basic_response(self):
        """Test parsing basic MCP tool response."""
        response = {
            "name": "test-tool",
            "description": "A test tool",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "input": {
                        "type": "string",
                        "description": "Input value",
                    }
                },
                "required": ["input"],
            },
        }
        tool = parse_mcp_tool_response(response)

        assert tool.name == "test-tool"
        assert tool.description == "A test tool"
        assert len(tool.parameters) == 1
        assert tool.parameters[0].name == "input"
        assert tool.parameters[0].required is True

    def test_parse_missing_name(self):
        """Test that missing name raises error."""
        response = {"description": "No name"}

        with pytest.raises(MCPMappingError, match="missing 'name'"):
            parse_mcp_tool_response(response)

    def test_parse_empty_schema(self):
        """Test parsing response with no input schema."""
        response = {
            "name": "simple-tool",
            "description": "Simple tool",
        }
        tool = parse_mcp_tool_response(response)

        assert tool.name == "simple-tool"
        assert tool.parameters == []


class TestValidateToolName:
    """Tests for validate_tool_name function."""

    def test_valid_names(self):
        """Test valid tool names."""
        assert validate_tool_name("my-tool") == []
        assert validate_tool_name("tool123") == []
        assert validate_tool_name("my_tool") == []
        assert validate_tool_name("a") == []

    def test_empty_name(self):
        """Test empty name."""
        errors = validate_tool_name("")
        assert "required" in errors[0].lower()

    def test_invalid_start(self):
        """Test name starting with non-letter."""
        errors = validate_tool_name("123tool")
        assert len(errors) > 0

    def test_uppercase(self):
        """Test uppercase letters."""
        errors = validate_tool_name("MyTool")
        assert len(errors) > 0

    def test_too_long(self):
        """Test name exceeding max length."""
        long_name = "a" * 65
        errors = validate_tool_name(long_name)
        assert "64 characters" in errors[0]


# =============================================================================
# MCPServerConfig Tests
# =============================================================================

class TestMCPServerConfig:
    """Tests for MCPServerConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = MCPServerConfig(name="test-server")

        assert config.name == "test-server"
        assert config.description == ""
        assert config.version == "1.0.0"
        assert config.host == "localhost"
        assert config.port == 8080
        assert config.tools == []

    def test_to_dict(self):
        """Test converting to dictionary."""
        config = MCPServerConfig(
            name="my-server",
            description="My server",
            port=9000,
            tools=["tool1", "tool2"],
        )
        data = config.to_dict()

        assert data["name"] == "my-server"
        assert data["description"] == "My server"
        assert data["server"]["port"] == 9000
        assert data["tools"] == ["tool1", "tool2"]

    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {
            "name": "restored-server",
            "description": "Restored",
            "server": {"host": "0.0.0.0", "port": 3000},
            "tools": ["tool-a"],
        }
        config = MCPServerConfig.from_dict(data)

        assert config.name == "restored-server"
        assert config.host == "0.0.0.0"
        assert config.port == 3000
        assert config.tools == ["tool-a"]

    def test_save_and_load(self, tmp_path):
        """Test saving and loading configuration."""
        server_dir = tmp_path / "server"
        server_dir.mkdir()

        original = MCPServerConfig(
            name="persistent-server",
            description="Persistent",
            port=4000,
        )
        original.save(server_dir)

        loaded = MCPServerConfig.load(server_dir)

        assert loaded.name == original.name
        assert loaded.description == original.description
        assert loaded.port == original.port


# =============================================================================
# MCPServerProject Tests
# =============================================================================

class TestMCPServerProject:
    """Tests for MCPServerProject class."""

    def test_create_project(self, tmp_path):
        """Test creating a new server project."""
        server_dir = tmp_path / "new-server"

        project = MCPServerProject.create(
            server_dir=server_dir,
            name="test-server",
            description="Test server",
        )

        assert server_dir.exists()
        assert (server_dir / SERVER_CONFIG_FILE).exists()
        assert (server_dir / "tools").is_dir()
        assert (server_dir / "server.py").exists()
        assert project.config.name == "test-server"

    def test_create_existing_fails(self, tmp_path):
        """Test that creating in existing directory fails."""
        server_dir = tmp_path / "existing"
        server_dir.mkdir()

        with pytest.raises(MCPServerError, match="already exists"):
            MCPServerProject.create(server_dir)

    def test_load_project(self, tmp_path):
        """Test loading an existing project."""
        # Create a project first
        server_dir = tmp_path / "load-test"
        MCPServerProject.create(server_dir, name="load-server")

        # Load it
        loaded = MCPServerProject.load(server_dir)

        assert loaded.config.name == "load-server"
        assert loaded.path == server_dir

    def test_add_skill(self, tmp_path):
        """Test adding a skill to server."""
        # Create server
        server_dir = tmp_path / "skill-server"
        project = MCPServerProject.create(server_dir)

        # Create skill
        skill_dir = tmp_path / "skills" / "test-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("""---
name: test-skill
description: A test skill
---

# Test Skill

Do something.
""")

        # Add skill
        tool = project.add_skill(skill_dir)

        assert tool.name == "test-skill"
        assert "test-skill" in project.config.tools
        assert (server_dir / "tools" / "test-skill.json").exists()

    def test_remove_tool(self, tmp_path):
        """Test removing a tool from server."""
        # Create server with a skill
        server_dir = tmp_path / "remove-server"
        project = MCPServerProject.create(server_dir)

        skill_dir = tmp_path / "skills" / "remove-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("""---
name: remove-skill
description: To be removed
---
Remove me.
""")

        project.add_skill(skill_dir)
        assert "remove-skill" in project.config.tools

        # Remove it
        removed = project.remove_tool("remove-skill")

        assert removed is True
        assert "remove-skill" not in project.config.tools
        assert not (server_dir / "tools" / "remove-skill.json").exists()

    def test_remove_nonexistent_tool(self, tmp_path):
        """Test removing a tool that doesn't exist."""
        server_dir = tmp_path / "empty-server"
        project = MCPServerProject.create(server_dir)

        removed = project.remove_tool("nonexistent")

        assert removed is False

    def test_list_tools(self, tmp_path):
        """Test listing tools in server."""
        server_dir = tmp_path / "list-server"
        project = MCPServerProject.create(server_dir)

        # Add two skills
        for name in ["skill-a", "skill-b"]:
            skill_dir = tmp_path / "skills" / name
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(f"""---
name: {name}
description: Skill {name}
---
Instructions for {name}.
""")
            project.add_skill(skill_dir)

        tools = project.list_tools()

        assert len(tools) == 2
        tool_names = [t.name for t in tools]
        assert "skill-a" in tool_names
        assert "skill-b" in tool_names

    def test_get_mcp_config(self, tmp_path):
        """Test getting MCP client configuration."""
        server_dir = tmp_path / "config-server"
        project = MCPServerProject.create(server_dir, name="my-mcp")

        mcp_config = project.get_mcp_config()

        assert "my-mcp" in mcp_config
        assert "command" in mcp_config["my-mcp"]
        assert "args" in mcp_config["my-mcp"]


# =============================================================================
# Server Module Functions Tests
# =============================================================================

class TestServerFunctions:
    """Tests for server module-level functions."""

    def test_init_server(self, tmp_path):
        """Test init_server function."""
        server_dir = tmp_path / "init-test"

        project = init_server(server_dir, name="init-server")

        assert project.config.name == "init-server"
        assert server_dir.exists()

    def test_load_server(self, tmp_path):
        """Test load_server function."""
        server_dir = tmp_path / "load-func-test"
        init_server(server_dir, name="load-func")

        project = load_server(server_dir)

        assert project.config.name == "load-func"

    def test_add_skill_to_server(self, tmp_path):
        """Test add_skill_to_server function."""
        server_dir = tmp_path / "add-func-test"
        init_server(server_dir)

        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
name: func-skill
description: Function test skill
---
Instructions.
""")

        tool = add_skill_to_server(server_dir, skill_dir)

        assert tool.name == "func-skill"

    def test_remove_tool_from_server(self, tmp_path):
        """Test remove_tool_from_server function."""
        server_dir = tmp_path / "remove-func-test"
        init_server(server_dir)

        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
name: remove-func-skill
description: To remove
---
X
""")
        add_skill_to_server(server_dir, skill_dir)

        removed = remove_tool_from_server(server_dir, "remove-func-skill")

        assert removed is True

    def test_list_server_tools(self, tmp_path):
        """Test list_server_tools function."""
        server_dir = tmp_path / "list-func-test"
        init_server(server_dir)

        tools = list_server_tools(server_dir)

        assert tools == []

    def test_is_mcp_server(self, tmp_path):
        """Test is_mcp_server function."""
        # Not a server
        assert is_mcp_server(tmp_path) is False

        # Create server
        server_dir = tmp_path / "check-server"
        init_server(server_dir)

        assert is_mcp_server(server_dir) is True


# =============================================================================
# MCPServerInfo Tests
# =============================================================================

class TestMCPServerInfo:
    """Tests for MCPServerInfo dataclass."""

    def test_from_config(self):
        """Test creating from config entry."""
        config = {
            "command": "python",
            "args": ["-m", "my_server"],
            "env": {"DEBUG": "1"},
        }
        info = MCPServerInfo.from_config("test-server", config)

        assert info.name == "test-server"
        assert info.command == "python"
        assert info.args == ["-m", "my_server"]
        assert info.env == {"DEBUG": "1"}

    def test_from_config_defaults(self):
        """Test creating with missing optional fields."""
        config = {}
        info = MCPServerInfo.from_config("minimal", config)

        assert info.name == "minimal"
        assert info.command == ""
        assert info.args == []
        assert info.env == {}


# =============================================================================
# DiscoveredTool Tests
# =============================================================================

class TestDiscoveredTool:
    """Tests for DiscoveredTool dataclass."""

    def test_basic_discovered_tool(self):
        """Test creating a discovered tool."""
        tool_def = MCPToolDefinition(
            name="discovered",
            description="A discovered tool",
        )
        discovered = DiscoveredTool(
            name="discovered",
            description="A discovered tool",
            server_name="my-server",
            tool_definition=tool_def,
        )

        assert discovered.name == "discovered"
        assert discovered.server_name == "my-server"
        assert discovered.tool_definition == tool_def


# =============================================================================
# Client Functions Tests
# =============================================================================

class TestClientFunctions:
    """Tests for client module functions."""

    def test_discover_tools_from_config_missing_file(self, tmp_path):
        """Test error when config file doesn't exist."""
        with pytest.raises(MCPClientError, match="not found"):
            discover_tools_from_config(tmp_path / "nonexistent.json")

    def test_discover_tools_from_config_invalid_json(self, tmp_path):
        """Test error on invalid JSON."""
        config_path = tmp_path / "invalid.json"
        config_path.write_text("not json")

        with pytest.raises(MCPClientError, match="Invalid JSON"):
            discover_tools_from_config(config_path)

    def test_discover_tools_from_config_no_servers(self, tmp_path):
        """Test config with no servers."""
        config_path = tmp_path / "empty.json"
        config_path.write_text(json.dumps({"mcpServers": {}}))

        tools = discover_tools_from_config(config_path)

        assert tools == []

    def test_list_configured_servers(self, tmp_path):
        """Test listing configured servers."""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({
            "mcpServers": {
                "server1": {"command": "python", "args": ["s1.py"]},
                "server2": {"command": "node", "args": ["s2.js"]},
            }
        }))

        servers = list_configured_servers(config_path)

        assert len(servers) == 2
        names = [s.name for s in servers]
        assert "server1" in names
        assert "server2" in names

    def test_list_configured_servers_no_config(self, tmp_path):
        """Test with no config file."""
        servers = list_configured_servers(tmp_path / "missing.json")

        assert servers == []

    def test_import_tool_as_skill(self, tmp_path):
        """Test importing a tool as a skill."""
        tool_def = MCPToolDefinition(
            name="imported-tool",
            description="An imported tool",
            parameters=[
                MCPToolParameter(
                    name="input",
                    description="Input value",
                    required=True,
                ),
            ],
        )
        discovered = DiscoveredTool(
            name="imported-tool",
            description="An imported tool",
            server_name="test-server",
            tool_definition=tool_def,
        )

        output_dir = tmp_path / "imported"
        skill_dir = import_tool_as_skill(discovered, output_dir)

        assert skill_dir.exists()
        assert (skill_dir / "SKILL.md").exists()
        skill_content = (skill_dir / "SKILL.md").read_text()
        assert "imported-tool" in skill_content

    def test_import_tool_existing_fails(self, tmp_path):
        """Test that importing over existing skill fails."""
        tool_def = MCPToolDefinition(
            name="existing-skill",
            description="Existing",
        )
        discovered = DiscoveredTool(
            name="existing-skill",
            description="Existing",
            server_name="server",
            tool_definition=tool_def,
        )

        output_dir = tmp_path / "output"
        # Create existing skill
        (output_dir / "existing-skill").mkdir(parents=True)

        with pytest.raises(MCPClientError, match="already exists"):
            import_tool_as_skill(discovered, output_dir)

    def test_get_claude_desktop_config_path(self):
        """Test getting Claude Desktop config path."""
        # This may or may not exist depending on the system
        path = get_claude_desktop_config_path()

        if path is not None:
            # If returned, it should be a Path
            assert isinstance(path, Path)


# =============================================================================
# Integration Tests
# =============================================================================

class TestMCPIntegration:
    """Integration tests for MCP workflow."""

    def test_skill_to_server_to_skill_roundtrip(self, tmp_path):
        """Test complete roundtrip: skill -> MCP server -> skill."""
        # 1. Create original skill
        skill_dir = tmp_path / "skills" / "original"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("""---
name: roundtrip-skill
description: Test roundtrip conversion
version: 1.0.0
---

# Roundtrip Skill

## Parameters

- `input` (string): The input to process (required)
- `format`: Output format

## Instructions

Process the input and return result.
""")

        # 2. Create MCP server and add skill
        server_dir = tmp_path / "server"
        project = init_server(server_dir, name="roundtrip-server")
        tool = project.add_skill(skill_dir)

        assert tool.name == "roundtrip-skill"
        assert tool.version == "1.0.0"

        # 3. Load tool definition
        loaded_tools = list_server_tools(server_dir)
        assert len(loaded_tools) == 1

        # 4. Convert back to skill
        restored_skill = mcp_tool_to_skill(loaded_tools[0])

        assert restored_skill.name == "roundtrip-skill"
        assert "input" in restored_skill.content
        assert "format" in restored_skill.content

    def test_generated_server_script(self, tmp_path):
        """Test that generated server script is valid Python."""
        # Create server with a skill
        server_dir = tmp_path / "script-test"
        project = init_server(server_dir)

        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
name: script-skill
description: Script test
---
Instructions.
""")
        project.add_skill(skill_dir)

        # Verify script is valid Python syntax
        script_path = server_dir / "server.py"
        assert script_path.exists()

        script_content = script_path.read_text()

        # Try to compile (syntax check)
        try:
            compile(script_content, script_path, "exec")
        except SyntaxError as e:
            pytest.fail(f"Generated server script has syntax error: {e}")

        # Check for expected content
        assert "from mcp.server import Server" in script_content
        assert "script-skill" in script_content
        assert "list_tools" in script_content
        assert "call_tool" in script_content
