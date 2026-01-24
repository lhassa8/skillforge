# SkillForge CLI Cheat Sheet

Quick reference for all SkillForge commands.

## Installation

```bash
pip install ai-skillforge        # Basic
pip install ai-skillforge[ai]    # With AI generation
```

## Creating Skills

| Command | Description |
|---------|-------------|
| `skillforge generate "description"` | AI-generate a complete skill |
| `skillforge new NAME` | Create skill scaffold |
| `skillforge new NAME --template X` | Create from template |
| `skillforge templates` | List available templates |
| `skillforge templates show NAME` | Preview a template |

### Examples

```bash
# AI generation
skillforge generate "Help write git commit messages"
skillforge generate "Review Python code" --name py-reviewer
skillforge generate "API helper" --context ./my-project

# Manual creation
skillforge new my-skill -d "Help with task X"
skillforge new my-skill --template code-review
```

## Validation & Testing

| Command | Description |
|---------|-------------|
| `skillforge validate PATH` | Validate skill structure |
| `skillforge test PATH` | Run tests (mock mode) |
| `skillforge test PATH --mode live` | Run tests with real API |
| `skillforge show PATH` | Display skill info |
| `skillforge preview PATH` | Preview as Claude sees it |

### Examples

```bash
# Validation
skillforge validate ./skills/my-skill
skillforge validate ./skills/my-skill --strict

# Testing
skillforge test ./skills/my-skill
skillforge test ./skills/my-skill --mode live
skillforge test ./skills/my-skill --tags smoke
skillforge test ./skills/my-skill --format junit -o results.xml
```

## Deployment

| Command | Description |
|---------|-------------|
| `skillforge install PATH` | Install to Claude Code (~/.claude/skills/) |
| `skillforge install PATH --project` | Install to project (./.claude/skills/) |
| `skillforge uninstall NAME` | Remove from Claude Code |
| `skillforge bundle PATH` | Create zip for claude.ai |
| `skillforge sync PATH` | Install all skills from directory |
| `skillforge installed` | List installed skills |

### Examples

```bash
# Claude Code
skillforge install ./skills/my-skill
skillforge install ./skills/my-skill --project
skillforge uninstall my-skill
skillforge installed

# claude.ai
skillforge bundle ./skills/my-skill
# Upload the .zip at Settings → Features → Custom Skills
```

## Hub Commands

| Command | Description |
|---------|-------------|
| `skillforge hub list` | List all hub skills |
| `skillforge hub search QUERY` | Search skills |
| `skillforge hub info NAME` | Show skill details |
| `skillforge hub install NAME` | Install from hub |
| `skillforge hub publish PATH` | Publish to hub |

### Examples

```bash
# Browse
skillforge hub list
skillforge hub search "code review"
skillforge hub search react
skillforge hub info code-reviewer

# Install
skillforge hub install code-reviewer
skillforge hub install docker-helper --project

# Publish
skillforge hub publish ./skills/my-skill
skillforge hub publish ./skills/my-skill -m "My first skill!"
```

## AI-Powered Commands

| Command | Description |
|---------|-------------|
| `skillforge improve PATH "request"` | Enhance skill with AI |
| `skillforge analyze PATH` | AI analysis and suggestions |
| `skillforge providers` | Check AI provider status |

### Examples

```bash
# Improve
skillforge improve ./skills/my-skill "Add more examples"
skillforge improve ./skills/my-skill "Handle edge cases" --dry-run

# Analyze
skillforge analyze ./skills/my-skill
skillforge analyze ./skills/my-skill --json
```

## Security & Governance

| Command | Description |
|---------|-------------|
| `skillforge security scan PATH` | Scan for vulnerabilities |
| `skillforge security patterns` | List security patterns |
| `skillforge governance trust PATH` | View/set trust tier |
| `skillforge governance policy list` | List policies |
| `skillforge governance audit` | View audit trail |

### Examples

```bash
# Security
skillforge security scan ./skills/my-skill
skillforge security scan ./skills/my-skill --fail-on-issues

# Governance
skillforge governance trust ./skills/my-skill
skillforge governance check ./skills/my-skill --policy production
```

## Versioning

| Command | Description |
|---------|-------------|
| `skillforge version show PATH` | Show skill version |
| `skillforge version bump PATH` | Bump patch version |
| `skillforge version bump PATH --minor` | Bump minor version |
| `skillforge version bump PATH --major` | Bump major version |
| `skillforge lock PATH` | Generate lock file |

### Examples

```bash
skillforge version show ./skills/my-skill
skillforge version bump ./skills/my-skill --minor
skillforge lock ./skills
```

## MCP Integration

| Command | Description |
|---------|-------------|
| `skillforge mcp init PATH` | Create MCP server project |
| `skillforge mcp add SERVER SKILL` | Add skill to server |
| `skillforge mcp serve SERVER` | Run MCP server |
| `skillforge mcp discover` | Find MCP tools |
| `skillforge mcp import TOOL` | Import MCP tool as skill |

### Examples

```bash
skillforge mcp init ./my-server
skillforge mcp add ./my-server ./skills/code-reviewer
skillforge mcp serve ./my-server
skillforge mcp config ./my-server  # Show Claude Desktop config
```

## Publishing

| Command | Description |
|---------|-------------|
| `skillforge publish PATH --platform X` | Publish to platform |
| `skillforge platforms` | List available platforms |

### Examples

```bash
skillforge publish ./skills/my-skill --platform claude
skillforge publish ./skills/my-skill --platform openai --mode gpt
skillforge publish ./skills/my-skill --all --dry-run
```

## Utility Commands

| Command | Description |
|---------|-------------|
| `skillforge doctor` | Check installation health |
| `skillforge info` | Show SkillForge info |
| `skillforge list PATH` | List skills in directory |
| `skillforge config show` | Show configuration |

## Environment Variables

```bash
# AI Providers
export ANTHROPIC_API_KEY=your-key
export OPENAI_API_KEY=your-key

# Configuration overrides
export SKILLFORGE_DEFAULT_MODEL=gpt-4o
export SKILLFORGE_LOG_LEVEL=debug
```

## Common Workflows

### Create and Deploy a Skill

```bash
# 1. Generate
skillforge generate "Help with X" --name my-skill

# 2. Test
skillforge test ./skills/my-skill

# 3. Deploy
skillforge install ./skills/my-skill
```

### Improve an Existing Skill

```bash
# 1. Analyze
skillforge analyze ./skills/my-skill

# 2. Improve
skillforge improve ./skills/my-skill "Add error handling examples"

# 3. Test
skillforge test ./skills/my-skill

# 4. Bump version
skillforge version bump ./skills/my-skill --minor
```

### Publish to Hub

```bash
# 1. Validate
skillforge validate ./skills/my-skill --strict

# 2. Test
skillforge test ./skills/my-skill

# 3. Security scan
skillforge security scan ./skills/my-skill --fail-on-issues

# 4. Publish
skillforge hub publish ./skills/my-skill
```

## Getting Help

```bash
skillforge --help              # General help
skillforge COMMAND --help      # Command-specific help
skillforge hub --help          # Subcommand help
```
