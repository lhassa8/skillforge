# SkillForge

[![PyPI version](https://badge.fury.io/py/skillforge.svg)](https://badge.fury.io/py/skillforge)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/lhassa8/skillforge/actions/workflows/tests.yml/badge.svg)](https://github.com/lhassa8/skillforge/actions/workflows/tests.yml)

**SkillForge** is a developer tool for creating, testing, and running deterministic "Skills" — reproducible, automated tasks that can be applied to any codebase.

Think of it as **infrastructure-as-code for developer workflows**: codify your setup scripts, deployment procedures, and project configurations as testable, shareable, version-controlled skills.

## Why SkillForge?

| Problem | SkillForge Solution |
|---------|---------------------|
| Shell scripts break silently | Skills have built-in validation checks |
| "Works on my machine" | Sandbox execution isolates changes |
| Hard to test automation | Fixture-based testing with golden artifacts |
| Sharing scripts is messy | Registry system for publishing and installing |
| Secrets in scripts | Encrypted secret management with auto-masking |
| Non-deterministic CI | Cassette recording for reproducible replays |

## Features

- **Declarative YAML skills** — Define steps, inputs, checks, and requirements
- **Sandbox execution** — Run skills safely without modifying original files
- **Fixture testing** — Test skills with known inputs and expected outputs
- **AI generation** — Generate skills from natural language (Claude, GPT, Ollama)
- **Secret management** — Encrypted storage with automatic log masking
- **Skill registry** — Share and discover skills via Git or local registries
- **Recording mode** — Record terminal sessions and compile into skills
- **GitHub Actions import** — Convert workflows to local skills
- **Cassette replay** — Record command outputs for deterministic testing

## Installation

```bash
pip install skillforge
```

### Optional Dependencies

```bash
# AI-powered skill generation
pip install skillforge[ai]        # Includes anthropic, openai

# Enhanced encryption
pip install skillforge[crypto]    # Includes cryptography (Fernet)

# All optional features
pip install skillforge[all]
```

### Requirements

- Python 3.10 or higher
- git (for recording and registry features)
- rsync (for sandbox creation)

Verify your setup:

```bash
skillforge doctor
```

## Quick Start

### 1. Initialize SkillForge

```bash
skillforge init
```

### 2. Create Your First Skill

```bash
skillforge new setup_project
```

### 3. Define the Skill

Edit `skills/setup_project/skill.yaml`:

```yaml
name: setup_project
version: "0.1.0"
description: "Initialize a Python project with common tooling"

inputs:
  - name: project_name
    type: string
    required: true
    description: "Name of the project"

steps:
  - id: create_venv
    type: shell
    name: "Create virtual environment"
    command: "python -m venv .venv"
    cwd: "{sandbox_dir}"

  - id: install_tools
    type: shell
    name: "Install development tools"
    command: ".venv/bin/pip install pytest black ruff"
    cwd: "{sandbox_dir}"

  - id: create_pyproject
    type: file.template
    name: "Create pyproject.toml"
    path: "{sandbox_dir}/pyproject.toml"
    template: |
      [project]
      name = "{project_name}"
      version = "0.1.0"

      [tool.black]
      line-length = 88

      [tool.ruff]
      line-length = 88

checks:
  - id: venv_exists
    type: dir_exists
    path: "{sandbox_dir}/.venv"

  - id: pyproject_exists
    type: file_exists
    path: "{sandbox_dir}/pyproject.toml"
```

### 4. Test the Skill

```bash
# Validate the skill definition
skillforge lint skills/setup_project

# Dry run (shows what would happen)
skillforge run skills/setup_project --target ./my-project --dry-run

# Run for real (in sandbox)
skillforge run skills/setup_project --target ./my-project --input project_name=myapp
```

## Core Concepts

### Skills

A **Skill** is a reproducible task defined in YAML:

```
my_skill/
├── skill.yaml          # Skill definition (steps, inputs, checks)
├── SKILL.txt           # Human-readable description
├── checks.py           # Custom validation functions (optional)
├── fixtures/           # Test cases
│   └── basic/
│       ├── input/      # Initial state
│       └── expected/   # Expected final state
├── cassettes/          # Recorded command outputs
└── reports/            # Execution reports
```

### Sandbox Execution

Skills run in an isolated sandbox by default. Your original files are copied to a temporary location, and all modifications happen there. This protects against unintended changes and enables safe testing.

```bash
# Run in sandbox (default, safe)
skillforge run my_skill --target ./project

# Run directly on target (dangerous, use with caution)
skillforge run my_skill --target ./project --no-sandbox
```

### Placeholders

Use placeholders in your skill definitions:

| Placeholder | Description |
|-------------|-------------|
| `{sandbox_dir}` | Working directory (sandbox or target) |
| `{target_dir}` | Original target directory path |
| `{skill_dir}` | Skill definition directory |
| `{input_name}` | Value of an input parameter |
| `{secret:name}` | Value from secret storage |

## Command Reference

### Creating Skills

```bash
# Create from scratch
skillforge new my_skill

# Generate with AI
skillforge ai generate "Set up a Node.js project with TypeScript and Jest"

# Import GitHub Actions workflow
skillforge import github-action .github/workflows/ci.yml

# Wrap existing script
skillforge wrap ./scripts/deploy.sh

# Record terminal session
skillforge record --name deploy --workdir ./project
# ... do your work ...
exit
skillforge compile rec_20240115_143022 --name deploy
```

### Running Skills

```bash
# Basic execution
skillforge run ./skills/my_skill --target ./project

# With inputs
skillforge run ./skills/my_skill --target ./project --input name=value

# With environment variables
skillforge run ./skills/my_skill --target ./project -e API_URL=https://api.example.com

# Dry run (preview only)
skillforge run ./skills/my_skill --target ./project --dry-run
```

### Testing Skills

```bash
# Validate skill definition
skillforge lint ./skills/my_skill

# Run fixture tests
skillforge test ./skills/my_skill

# Create golden artifacts for regression testing
skillforge bless ./skills/my_skill --fixture basic

# Record command outputs for deterministic replay
skillforge cassette record ./skills/my_skill --fixture basic
skillforge cassette replay ./skills/my_skill --fixture basic
```

### Skill Registry

```bash
# Add a registry
skillforge registry add company https://github.com/company/skills-registry

# Search for skills
skillforge search docker

# Install a skill
skillforge install setup-python

# List installed skills
skillforge installed

# Update skills
skillforge update --check
skillforge update
```

### Secret Management

```bash
# Store a secret (prompts for value)
skillforge secret set API_KEY

# Store with value
skillforge secret set DB_URL --value "postgresql://..."

# List secrets
skillforge secret list

# Use in skills with {secret:name} syntax
```

## AI-Powered Generation

Generate skills from natural language descriptions:

```bash
# Basic generation
skillforge ai generate "Create a Docker development environment"

# With project context
skillforge ai generate "Add CI/CD pipeline" --target ./my-project

# Refine existing skill
skillforge ai refine ./skills/deploy "Add rollback on failure"

# Explain what a skill does
skillforge ai explain ./skills/complex_deploy
```

### Supported Providers

| Provider | Setup | Models |
|----------|-------|--------|
| Anthropic | `export ANTHROPIC_API_KEY=...` | claude-sonnet-4-20250514 (default) |
| OpenAI | `export OPENAI_API_KEY=...` | gpt-4o (default) |
| Ollama | `ollama serve` | llama3.2, codellama, etc. |

Check provider status:

```bash
skillforge ai providers
```

## Secret Management

SkillForge provides encrypted secret storage with automatic log masking.

### Backends

| Backend | Priority | Description |
|---------|----------|-------------|
| `env` | 1 | Environment variables (`SKILLFORGE_SECRET_*`) |
| `file` | 2 | Encrypted local storage (`~/.skillforge/secrets/`) |
| `vault` | 3 | HashiCorp Vault integration |

### Usage in Skills

```yaml
steps:
  - id: deploy
    type: shell
    command: "deploy --token {secret:deploy_token}"
    env:
      DATABASE_URL: "{secret:database_url}"
```

Secrets are:
- Encrypted at rest (Fernet or XOR-based)
- Automatically masked in logs and reports
- Never stored in plain text

## Skill Definition Reference

### Step Types

| Type | Description |
|------|-------------|
| `shell` | Execute a shell command |
| `python` | Run Python code or module |
| `file.template` | Create file from template |
| `file.replace` | Replace content in file |
| `json.patch` | Patch JSON file |
| `yaml.patch` | Patch YAML file |

### Check Types

| Type | Description |
|------|-------------|
| `exit_code` | Verify step exit code |
| `file_exists` | Verify file exists |
| `file_contains` | Verify file contains string |
| `file_not_contains` | Verify file doesn't contain string |
| `dir_exists` | Verify directory exists |
| `custom` | Run custom Python function |

### Full skill.yaml Example

```yaml
name: setup_node_project
version: "1.0.0"
description: "Initialize a Node.js project with TypeScript"

inputs:
  - name: project_name
    type: string
    required: true
  - name: node_version
    type: string
    default: "20"

requirements:
  commands:
    - node
    - npm

preconditions:
  - "Node.js must be installed"

steps:
  - id: init
    type: shell
    name: "Initialize npm project"
    command: "npm init -y"
    cwd: "{sandbox_dir}"

  - id: install_typescript
    type: shell
    name: "Install TypeScript"
    command: "npm install -D typescript @types/node"
    cwd: "{sandbox_dir}"

  - id: create_tsconfig
    type: file.template
    path: "{sandbox_dir}/tsconfig.json"
    template: |
      {
        "compilerOptions": {
          "target": "ES2022",
          "module": "commonjs",
          "strict": true,
          "outDir": "./dist"
        }
      }

  - id: update_package
    type: json.patch
    path: "{sandbox_dir}/package.json"
    operations:
      - op: add
        path: /scripts/build
        value: "tsc"

checks:
  - id: typescript_installed
    type: file_exists
    path: "{sandbox_dir}/node_modules/typescript"

  - id: tsconfig_exists
    type: file_exists
    path: "{sandbox_dir}/tsconfig.json"
```

## Configuration

Configuration file: `~/.skillforge/config.yaml`

```yaml
# Default output directory for new skills
default_skills_dir: ./skills

# Default shell for recording
default_shell: bash

# Sandbox settings
sandbox:
  cleanup: true
  base_dir: /tmp/skillforge

# Registry settings
registries:
  - name: default
    url: https://github.com/skillforge/registry
    type: git
    priority: 50
```

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

# Type checking
mypy skillforge/

# Linting
ruff check skillforge/
```

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.
