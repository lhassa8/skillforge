# SkillForge Examples

This directory contains example skills and tutorials to help you get started with SkillForge.

## Example Skills

| Skill | Description | Features Demonstrated |
|-------|-------------|----------------------|
| [code-reviewer](./skills/code-reviewer/) | Review code for issues | Basic skill, tests |
| [git-commit](./skills/git-commit/) | Write commit messages | Templates, examples |
| [api-documenter](./skills/api-documenter/) | Generate API docs | Composite skill (includes) |
| [data-analyst](./skills/data-analyst/) | Analyze data files | Versioning, metadata |

## Tutorials

Step-by-step guides for common workflows:

1. [Getting Started](./tutorials/01-getting-started.md) - Create your first skill
2. [Testing Skills](./tutorials/02-testing-skills.md) - Write and run tests
3. [Security & Governance](./tutorials/03-security-governance.md) - Scan and secure skills
4. [Multi-Platform Publishing](./tutorials/04-multi-platform.md) - Deploy everywhere
5. [MCP Integration](./tutorials/05-mcp-integration.md) - Expose skills as MCP tools

## Quick Start

```bash
# Install SkillForge
pip install ai-skillforge[ai]

# Try an example skill
cd examples/skills/code-reviewer
skillforge validate .
skillforge test .
skillforge preview .

# Generate your own
skillforge generate "Help debug Python errors"
```

## Running Examples

Each example skill can be:

```bash
# Validated
skillforge validate ./skills/code-reviewer

# Tested
skillforge test ./skills/code-reviewer

# Previewed
skillforge preview ./skills/code-reviewer

# Installed to Claude Code
skillforge install ./skills/code-reviewer

# Bundled for claude.ai
skillforge bundle ./skills/code-reviewer
```
