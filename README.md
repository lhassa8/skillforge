# SkillForge

[![PyPI version](https://badge.fury.io/py/skillforge.svg)](https://badge.fury.io/py/skillforge)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/lhassa8/skillforge/actions/workflows/tests.yml/badge.svg)](https://github.com/lhassa8/skillforge/actions/workflows/tests.yml)

**SkillForge** is a CLI tool for creating, validating, and bundling [Anthropic Agent Skills](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills) — custom instructions that extend Claude's capabilities for specific tasks.

## What are Anthropic Agent Skills?

Agent Skills are custom capabilities you can add to Claude. Each skill provides instructions that Claude follows when triggered, allowing you to:

- Define specialized workflows for Claude to execute
- Include reference documentation Claude can access
- Bundle executable scripts Claude can run
- Share reusable capabilities across projects

## Installation

```bash
pip install skillforge
```

Verify your setup:

```bash
skillforge doctor
```

## Quick Start

### 1. Create a New Skill

```bash
skillforge new pdf-extractor -d "Extract text and tables from PDF files. Use when the user asks to analyze a PDF document."
```

This creates:
```
skills/pdf-extractor/
└── SKILL.md          # Skill definition with YAML frontmatter
```

### 2. Edit the Skill

Edit `skills/pdf-extractor/SKILL.md`:

```markdown
---
name: pdf-extractor
description: Extract text and tables from PDF files. Use when the user asks to analyze a PDF document.
---

# PDF Extractor

## Instructions

When the user provides a PDF file or asks about PDF content:

1. Use the `pdftotext` command to extract text content
2. For tables, use `tabula-py` or similar tools
3. Present the extracted content in a clear, formatted way

## Examples

### Example 1: Extract all text

**User request:** "Extract the text from report.pdf"

**What to do:**
1. Run `pdftotext report.pdf -`
2. Format and present the extracted text

### Example 2: Extract tables

**User request:** "Get the data table from page 3 of spreadsheet.pdf"

**What to do:**
1. Use tabula to extract tables from page 3
2. Format as markdown table or CSV
```

### 3. Validate the Skill

```bash
skillforge validate skills/pdf-extractor
```

### 4. Bundle for Upload

```bash
skillforge bundle skills/pdf-extractor
```

This creates a zip file you can upload to:
- **claude.ai**: Settings → Features → Upload Skill
- **API**: POST /v1/skills with the zip file

## Commands

### `skillforge new`

Create a new skill scaffold.

```bash
# Basic skill
skillforge new my-skill

# With description
skillforge new my-skill -d "Description of what the skill does"

# With scripts directory
skillforge new my-skill --with-scripts

# Custom output directory
skillforge new my-skill --out ./custom/path
```

### `skillforge validate`

Validate a skill against Anthropic requirements.

```bash
# Basic validation
skillforge validate ./skills/my-skill

# Strict mode (warnings become errors)
skillforge validate ./skills/my-skill --strict
```

### `skillforge bundle`

Bundle a skill into a zip file for upload.

```bash
# Bundle with auto-generated filename
skillforge bundle ./skills/my-skill

# Custom output path
skillforge bundle ./skills/my-skill -o my-skill.zip

# Skip validation (not recommended)
skillforge bundle ./skills/my-skill --no-validate
```

### `skillforge show`

Display skill details.

```bash
skillforge show ./skills/my-skill
```

### `skillforge preview`

Preview how Claude will see the skill.

```bash
skillforge preview ./skills/my-skill
```

### `skillforge list`

List all skills in a directory.

```bash
skillforge list ./skills
```

### `skillforge init`

Initialize a directory for skill development.

```bash
skillforge init
```

### `skillforge add`

Add reference documents or scripts to a skill.

```bash
# Add a reference document
skillforge add ./skills/my-skill doc REFERENCE

# Add a Python script
skillforge add ./skills/my-skill script helper

# Add a Bash script
skillforge add ./skills/my-skill script build --language bash
```

### `skillforge doctor`

Check your environment.

```bash
skillforge doctor
```

## SKILL.md Format

Every skill requires a `SKILL.md` file with YAML frontmatter:

```markdown
---
name: skill-name
description: Brief description. Explain when Claude should use this skill.
---

# Skill Title

Your skill instructions go here. This content is loaded when the skill is triggered.

## Instructions

Clear, step-by-step guidance for Claude.

## Examples

Show Claude how to handle common scenarios.
```

### Frontmatter Requirements

| Field | Requirements |
|-------|-------------|
| `name` | Required. Max 64 chars. Lowercase letters, numbers, hyphens only. Cannot contain "anthropic" or "claude". |
| `description` | Required. Max 1024 chars. Should explain when to use the skill. Cannot contain XML tags. |

### Best Practices

1. **Clear trigger conditions**: Use phrases like "Use when..." in the description
2. **Step-by-step instructions**: Be specific about what Claude should do
3. **Include examples**: Show common request/response patterns
4. **Reference additional files**: Link to `REFERENCE.md` or scripts when needed

## Skill Structure

A skill can include multiple files:

```
my-skill/
├── SKILL.md           # Required: Main skill definition
├── REFERENCE.md       # Optional: Additional documentation
├── API.md             # Optional: API documentation
└── scripts/           # Optional: Executable scripts
    ├── helper.py      # Claude can run these
    └── build.sh
```

### Additional Markdown Files

Create extra `.md` files for detailed reference documentation that Claude can access when needed:

```bash
skillforge add ./skills/my-skill doc API-REFERENCE
```

### Scripts Directory

Add executable scripts that Claude can run:

```bash
skillforge add ./skills/my-skill script analyze --language python
```

Scripts are executed when Claude needs them — the script code itself is not loaded into context, only the output.

## Development

```bash
# Clone the repository
git clone https://github.com/lhassa8/skillforge.git
cd skillforge

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=skillforge
```

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Resources

- [Anthropic Agent Skills Documentation](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills)
- [Changelog](CHANGELOG.md)
