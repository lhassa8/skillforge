# Tutorial 5: MCP Integration

Expose your skills as Model Context Protocol (MCP) tools for Claude Desktop and other MCP clients.

## What is MCP?

The [Model Context Protocol](https://modelcontextprotocol.io/) is an open standard for connecting AI models to external tools and data sources. SkillForge can:

1. **Export skills as MCP tools** - Run an MCP server exposing your skills
2. **Import MCP tools as skills** - Convert existing MCP tools to SkillForge skills

## Creating an MCP Server

### Initialize Server Project

```bash
skillforge mcp init ./my-mcp-server

# Output:
# ✓ Created MCP server: my-mcp-server/
#   - server.json (configuration)
#   - tools/ (tool definitions)
```

### Add Skills to Server

```bash
# Add a skill as an MCP tool
skillforge mcp add ./my-mcp-server ./skills/code-reviewer

# Add multiple skills
skillforge mcp add ./my-mcp-server ./skills/git-commit
skillforge mcp add ./my-mcp-server ./skills/api-documenter
```

### List Server Tools

```bash
skillforge mcp list ./my-mcp-server

# Output:
# Tools in my-mcp-server:
#
# 1. code-reviewer
#    Description: Review code for bugs and security issues
#
# 2. git-commit
#    Description: Write conventional commit messages
#
# 3. api-documenter
#    Description: Generate API documentation
```

### Remove a Tool

```bash
skillforge mcp remove ./my-mcp-server code-reviewer
```

## Running the MCP Server

### Start Server

```bash
skillforge mcp serve ./my-mcp-server

# Server runs on stdio transport (for Claude Desktop)
```

### Get Claude Desktop Config

```bash
skillforge mcp config ./my-mcp-server

# Output:
# Add this to your Claude Desktop config:
#
# {
#   "mcpServers": {
#     "my-mcp-server": {
#       "command": "skillforge",
#       "args": ["mcp", "serve", "/path/to/my-mcp-server"]
#     }
#   }
# }
```

### Configure Claude Desktop

1. Open Claude Desktop settings
2. Navigate to MCP configuration
3. Add the server configuration
4. Restart Claude Desktop

**Config file locations:**
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

## Discovering MCP Tools

### From Claude Desktop Config

```bash
# Auto-detect configured MCP servers
skillforge mcp discover

# Output:
# Discovered MCP tools:
#
# From: filesystem-server
#   - read_file: Read contents of a file
#   - write_file: Write contents to a file
#   - list_directory: List directory contents
#
# From: github-server
#   - search_repos: Search GitHub repositories
#   - get_file: Get file from repository
```

### From Custom Config

```bash
skillforge mcp discover --config ./my-mcp-config.json
```

## Importing MCP Tools as Skills

### Import a Tool

```bash
skillforge mcp import read_file

# Output:
# ✓ Imported MCP tool as skill: skills/read-file/
```

### Import with Custom Output

```bash
skillforge mcp import search_repos --output ./my-skills
```

### Import from Specific Server

```bash
skillforge mcp import github:get_file
```

## MCP Server Project Structure

```
my-mcp-server/
├── server.json          # Server configuration
└── tools/
    ├── code-reviewer.json
    ├── git-commit.json
    └── api-documenter.json
```

### server.json

```json
{
  "name": "my-mcp-server",
  "version": "1.0.0",
  "description": "My custom MCP tools",
  "tools": [
    "code-reviewer",
    "git-commit",
    "api-documenter"
  ]
}
```

### Tool Definition

```json
{
  "name": "code-reviewer",
  "description": "Review code for bugs and security issues",
  "inputSchema": {
    "type": "object",
    "properties": {
      "code": {
        "type": "string",
        "description": "The code to review"
      },
      "language": {
        "type": "string",
        "description": "Programming language"
      }
    },
    "required": ["code"]
  }
}
```

## Programmatic Usage

### Convert Skill to MCP Tool

```python
from skillforge.api import Skill, skill_to_mcp_tool

skill = Skill.from_directory("./skills/code-reviewer")
mcp_tool = skill_to_mcp_tool(skill)

print(mcp_tool.name)  # "code-reviewer"
print(mcp_tool.description)
print(mcp_tool.input_schema)
```

### Create MCP Server

```python
from skillforge.api import create_mcp_server

server = create_mcp_server(
    path="./my-server",
    name="My Tools",
    description="Custom MCP tools"
)
```

## Best Practices

1. **Clear descriptions**: MCP clients show tool descriptions to help the model choose
2. **Input schemas**: Define clear input parameters for predictable behavior
3. **Error handling**: Return helpful error messages
4. **Testing**: Test tools with `skillforge mcp serve` before deploying

## Example: Full Workflow

```bash
# 1. Create skills
skillforge generate "Format SQL queries" --name sql-formatter
skillforge generate "Explain code" --name code-explainer

# 2. Test skills
skillforge test ./skills/sql-formatter
skillforge test ./skills/code-explainer

# 3. Create MCP server
skillforge mcp init ./dev-tools-server

# 4. Add skills
skillforge mcp add ./dev-tools-server ./skills/sql-formatter
skillforge mcp add ./dev-tools-server ./skills/code-explainer

# 5. Get config for Claude Desktop
skillforge mcp config ./dev-tools-server

# 6. Run server (or configure Claude Desktop to run it)
skillforge mcp serve ./dev-tools-server
```

## Resources

- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [Claude Desktop MCP Documentation](https://docs.anthropic.com/en/docs/claude-desktop/mcp)
- [MCP Servers Repository](https://github.com/modelcontextprotocol/servers)
