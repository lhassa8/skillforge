# SkillForge

[![PyPI version](https://badge.fury.io/py/skillforge.svg)](https://badge.fury.io/py/skillforge)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/lhassa8/skillforge/actions/workflows/tests.yml/badge.svg)](https://github.com/lhassa8/skillforge/actions/workflows/tests.yml)

**SkillForge** is a CLI tool for creating, validating, and bundling [Anthropic Agent Skills](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills) — custom instructions that extend Claude's capabilities for specific tasks.

## Features

- **AI-Powered Generation** — Generate complete, high-quality skills from natural language descriptions
- **Validation** — Check skills against Anthropic's requirements before upload
- **Bundling** — Package skills as zip files ready for claude.ai or API upload
- **Skill Improvement** — Use AI to enhance existing skills with better examples and instructions

## Installation

```bash
pip install skillforge

# For AI-powered generation (recommended)
pip install skillforge[ai]
```

Verify your setup:

```bash
skillforge doctor
skillforge providers  # Check AI provider status
```

## Quick Start

### Generate a Skill with AI

The fastest way to create a skill:

```bash
# Set your API key
export ANTHROPIC_API_KEY=your-key

# Generate a complete skill from a description
skillforge generate "Help users write clear, conventional git commit messages"
```

This creates a complete, ready-to-use skill with instructions and examples.

### Or Create Manually

```bash
# Create a skill scaffold
skillforge new commit-helper -d "Help write git commit messages. Use when the user asks for help with commits."

# Edit the generated SKILL.md with your instructions
# Then validate and bundle
skillforge validate ./skills/commit-helper
skillforge bundle ./skills/commit-helper
```

## AI-Powered Commands

### `skillforge generate`

Generate a complete skill using AI.

```bash
# Basic generation
skillforge generate "Review Python code for best practices and security issues"

# With a custom name
skillforge generate "Analyze CSV data files" --name csv-analyzer

# With project context (AI analyzes your codebase)
skillforge generate "Help with this project's API" --context ./my-project

# Specify provider and model
skillforge generate "Debug JavaScript errors" --provider anthropic --model claude-sonnet-4-20250514
```

### `skillforge improve`

Enhance an existing skill using AI.

```bash
# Add more examples
skillforge improve ./skills/my-skill "Add 3 more detailed examples"

# Make instructions clearer
skillforge improve ./skills/my-skill "Make the instructions more specific and actionable"

# Add error handling
skillforge improve ./skills/my-skill "Add guidance for edge cases and error scenarios"

# Preview changes without saving
skillforge improve ./skills/my-skill "Restructure for clarity" --dry-run
```

### `skillforge providers`

Check which AI providers are available.

```bash
skillforge providers
```

**Supported Providers:**

| Provider | Setup | Models |
|----------|-------|--------|
| Anthropic | `export ANTHROPIC_API_KEY=...` | claude-sonnet-4-20250514, claude-opus-4-1-20250219 |
| OpenAI | `export OPENAI_API_KEY=...` | gpt-4o, gpt-4-turbo |
| Ollama | `ollama serve` | llama3.2, codellama, etc. |

## Other Commands

### `skillforge new`

Create a new skill scaffold.

```bash
skillforge new my-skill -d "Description of what the skill does"
skillforge new my-skill --with-scripts  # Include scripts directory
```

### `skillforge validate`

Validate a skill against Anthropic requirements.

```bash
skillforge validate ./skills/my-skill
skillforge validate ./skills/my-skill --strict  # Warnings become errors
```

### `skillforge bundle`

Bundle a skill into a zip file for upload.

```bash
skillforge bundle ./skills/my-skill
skillforge bundle ./skills/my-skill -o my-skill.zip
```

### `skillforge show` / `skillforge preview`

Display skill details or preview how Claude sees it.

```bash
skillforge show ./skills/my-skill
skillforge preview ./skills/my-skill
```

### `skillforge list`

List all skills in a directory.

```bash
skillforge list ./skills
```

### `skillforge add`

Add reference documents or scripts to a skill.

```bash
skillforge add ./skills/my-skill doc REFERENCE
skillforge add ./skills/my-skill script helper --language python
```

## SKILL.md Format

Every skill requires a `SKILL.md` file with YAML frontmatter:

```markdown
---
name: skill-name
description: Brief description. Explain when Claude should use this skill.
---

# Skill Title

Your skill instructions go here.

## Instructions

Clear, step-by-step guidance for Claude.

## Examples

### Example 1: [Scenario]

**User request:** "..."

**What to do:**
1. Step one
2. Step two
```

### Frontmatter Requirements

| Field | Requirements |
|-------|-------------|
| `name` | Max 64 chars. Lowercase letters, numbers, hyphens only. Cannot contain "anthropic" or "claude". |
| `description` | Max 1024 chars. Should explain when to use the skill. Cannot contain XML tags. |

## Skill Structure

```
my-skill/
├── SKILL.md           # Required: Main skill definition
├── REFERENCE.md       # Optional: Additional documentation
└── scripts/           # Optional: Executable scripts
    └── helper.py
```

## Development

```bash
git clone https://github.com/lhassa8/skillforge.git
cd skillforge
pip install -e ".[dev]"
pytest tests/ -v
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Resources

- [Anthropic Agent Skills Documentation](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills)
- [Changelog](CHANGELOG.md)
