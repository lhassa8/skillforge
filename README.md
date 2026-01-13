# SkillForge

A local-first developer tool to create, test, and run deterministic "Skills" - reproducible, automated tasks that can be applied to any codebase.

## Installation

```bash
# Clone the repository
git clone https://github.com/your-org/skillforge.git
cd skillforge

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e .
```

## Quick Start

```bash
# Initialize SkillForge
skillforge init

# Verify your environment
skillforge doctor

# Create a new skill
skillforge new my_first_skill

# Edit the skill definition
$EDITOR skills/my_first_skill/skill.yaml

# Lint the skill
skillforge lint skills/my_first_skill

# Run the skill against a target directory
skillforge run skills/my_first_skill --target ./my-project

# Test the skill with fixtures
skillforge test skills/my_first_skill
```

## Core Concepts

### Skills

A **Skill** is a reproducible, automated task defined in YAML. Each skill contains:

- **Steps**: Shell commands or file operations to execute
- **Inputs**: Parameters the skill accepts
- **Checks**: Validations to verify the skill succeeded
- **Fixtures**: Test cases with known inputs and expected outputs

### Skill Directory Structure

```
my_skill/
├── skill.yaml          # Skill definition
├── SKILL.txt           # Human-readable description
├── checks.py           # Custom check functions
├── fixtures/           # Test fixtures
│   └── happy_path/
│       ├── fixture.yaml
│       ├── input/      # Initial state
│       └── expected/   # Expected final state
├── cassettes/          # Recorded command outputs
└── reports/            # Execution reports
```

### Sandbox Execution

Skills run in an isolated sandbox by default. The target directory is copied to a temporary location, and all modifications happen there. This protects your original files from unintended changes.

## Commands

### Environment Setup

#### `skillforge init`

Initialize SkillForge configuration in your home directory.

```bash
skillforge init
```

Creates `~/.skillforge/` with default settings.

#### `skillforge doctor`

Verify your environment has all required dependencies.

```bash
skillforge doctor
```

Checks for Python version, git, rsync, and other requirements.

### Creating Skills

#### `skillforge new`

Create a new skill scaffold with boilerplate files.

```bash
# Basic usage
skillforge new my_skill

# With description
skillforge new deploy_app --description "Deploy application to production"

# Custom output directory
skillforge new my_skill --out ./custom/path
```

#### `skillforge generate`

Generate a skill from a human-readable spec file.

```bash
skillforge generate --from spec.txt --out ./skills
```

**Spec file format:**

```
SKILL: setup_project
DESCRIPTION: Initialize a new Node.js project
VERSION: 0.1.0

INPUTS:
- target_dir: path (required) - Target directory
- project_name: string (default: "my-app") - Project name

STEPS:
1. Initialize npm
   shell: npm init -y
   cwd: {target_dir}

2. Install dependencies
   shell: npm install express
   cwd: {target_dir}

CHECKS:
- file_exists: {sandbox_dir}/package.json
- exit_code: step1 equals 0
```

#### `skillforge wrap`

Wrap an existing script as a skill.

```bash
# Wrap a bash script
skillforge wrap ./deploy.sh

# Wrap with custom name
skillforge wrap ./build.py --name my_build_skill

# Override detected script type
skillforge wrap ./script --type python

# Custom output directory
skillforge wrap ./script.sh --out ./my-skills
```

Supports: bash, shell, python, node, ruby, perl

#### `skillforge import github-action`

Import a GitHub Actions workflow as a skill.

```bash
# Import a workflow
skillforge import github-action .github/workflows/ci.yml

# Import specific job
skillforge import github-action .github/workflows/ci.yml --job build

# Custom output
skillforge import github-action workflow.yml --out ./skills
```

Shell steps (`run:`) are converted directly. Action steps (`uses:`) are added as placeholders requiring manual conversion.

### AI-Powered Skill Generation

Use natural language to generate skills with AI. Supports multiple providers: Anthropic Claude, OpenAI GPT, and local Ollama models.

#### Setup

Configure your preferred AI provider:

```bash
# Option 1: Anthropic Claude (recommended)
export ANTHROPIC_API_KEY=your-api-key
pip install anthropic

# Option 2: OpenAI GPT
export OPENAI_API_KEY=your-api-key
pip install openai

# Option 3: Ollama (local, no API key needed)
ollama serve  # Start Ollama server
```

Check provider status:

```bash
skillforge ai providers
```

#### `skillforge ai generate`

Generate a skill from natural language description.

```bash
# Basic generation
skillforge ai generate "Set up a Python project with pytest and black"

# With project context (analyzes target directory)
skillforge ai generate "Add Docker support" --target ./myproject

# Using specific provider
skillforge ai generate "Create CI workflow" --provider openai

# With custom model
skillforge ai generate "Deploy to AWS" --provider anthropic --model claude-3-haiku-20240307

# With additional requirements
skillforge ai generate "Set up monitoring" --requirements "Use Prometheus, include Grafana dashboards"
```

The AI will:
1. Analyze your project structure (if `--target` provided)
2. Generate a complete skill.yaml with steps and checks
3. Create the skill directory with all boilerplate files
4. Validate the output and suggest next steps

#### `skillforge ai refine`

Refine an existing skill based on feedback.

```bash
# Fix issues
skillforge ai refine ./skills/my_skill "Add error handling for missing files"

# Improve structure
skillforge ai refine ./skills/my_skill "Split into smaller steps"

# Add features
skillforge ai refine ./skills/my_skill "Add support for TypeScript projects"
```

#### `skillforge ai explain`

Generate a plain-English explanation of what a skill does.

```bash
skillforge ai explain ./skills/deploy_app
```

Useful for understanding complex skills or generating documentation.

### Recording Skills

Record your terminal session to create skills from real work.

#### `skillforge record`

Start a recording session.

```bash
# Start recording
skillforge record --name deploy_process --workdir ./my-project

# Use zsh instead of bash
skillforge record -n setup -w . --shell zsh
```

This launches an interactive shell where all commands are captured. Type `exit` when done.

#### `skillforge stop`

Stop the active recording session (from another terminal).

```bash
skillforge stop
```

#### `skillforge compile`

Compile a recording into a skill.

```bash
# Compile with default name
skillforge compile rec_20240115_143022

# Custom skill name and output
skillforge compile rec_20240115_143022 --name deploy --out ./skills
```

#### `skillforge recording list`

List all recording sessions.

```bash
skillforge recording list
```

#### `skillforge recording show`

Show details of a recording.

```bash
skillforge recording show rec_20240115_143022
```

#### `skillforge recording delete`

Delete a recording session.

```bash
skillforge recording delete rec_20240115_143022
```

### Running Skills

#### `skillforge run`

Execute a skill against a target directory.

```bash
# Basic run (uses sandbox)
skillforge run ./skills/my_skill --target ./my-project

# Dry run - show plan without executing
skillforge run ./skills/my_skill --target ./my-project --dry-run

# Run without sandbox (dangerous - modifies target directly)
skillforge run ./skills/my_skill --target ./my-project --no-sandbox

# Pass environment variables
skillforge run ./skills/my_skill --target ./my-project -e API_KEY=secret -e DEBUG=1

# Custom sandbox directory
skillforge run ./skills/my_skill --target ./my-project --sandbox /tmp/my-sandbox
```

#### `skillforge lint`

Validate skill structure and check for issues.

```bash
skillforge lint ./skills/my_skill
```

Reports errors and warnings about:
- Missing required fields
- Invalid step configurations
- Undefined input references
- Missing fixtures

### Testing Skills

#### `skillforge test`

Run fixture tests for a skill.

```bash
# Run all fixtures
skillforge test ./skills/my_skill

# Run specific fixture
skillforge test ./skills/my_skill --fixture happy_path

# Verbose output
skillforge test ./skills/my_skill --verbose
```

#### `skillforge bless`

Run a skill and store the output as golden artifacts for regression testing.

```bash
# Bless a fixture
skillforge bless ./skills/my_skill --fixture happy_path

# Overwrite existing golden artifacts
skillforge bless ./skills/my_skill --fixture happy_path --force
```

Creates `_golden/` directory with:
- `expected_changed_files.json` - List of files modified
- `expected_hashes.json` - SHA256 hashes of file contents
- `bless_metadata.json` - Timestamp and context

### Cassettes (Deterministic Replay)

Cassettes record command outputs for deterministic test replay.

#### `skillforge cassette record`

Record command outputs during skill execution.

```bash
skillforge cassette record ./skills/my_skill --fixture happy_path
```

#### `skillforge cassette replay`

Replay recorded outputs instead of executing commands.

```bash
skillforge cassette replay ./skills/my_skill --fixture happy_path
```

#### `skillforge cassette list`

List all cassettes for a skill.

```bash
skillforge cassette list ./skills/my_skill
```

#### `skillforge cassette show`

Show details of a cassette.

```bash
skillforge cassette show ./skills/my_skill --fixture happy_path
```

## Skill Definition Reference

### skill.yaml

```yaml
name: my_skill
version: "0.1.0"
description: "What this skill does"

# Input parameters
inputs:
  - name: target_dir
    type: path
    description: "Target directory"
    required: true
  - name: message
    type: string
    description: "Optional message"
    required: false
    default: "Hello"

# Preconditions (documentation)
preconditions:
  - "Git must be installed"
  - "Node.js >= 18 required"

# Requirements
requirements:
  commands:
    - git
    - node

# Execution steps
steps:
  - id: step1
    type: shell
    name: "Initialize project"
    command: "npm init -y"
    cwd: "{sandbox_dir}"
    env:
      NODE_ENV: production

  - id: step2
    type: file.template
    name: "Create config"
    path: "{sandbox_dir}/config.json"
    template: |
      {
        "message": "{message}"
      }

# Validation checks
checks:
  - id: check1
    type: exit_code
    step_id: step1
    equals: 0

  - id: check2
    type: file_exists
    path: "{sandbox_dir}/package.json"

  - id: check3
    type: file_contains
    path: "{sandbox_dir}/config.json"
    contains: "Hello"
```

### Placeholders

Use placeholders in commands and paths:

| Placeholder | Description |
|-------------|-------------|
| `{target_dir}` | Original target directory |
| `{sandbox_dir}` | Sandbox working directory |
| `{skill_dir}` | Skill definition directory |
| `{input_name}` | Value of input parameter |

### Step Types

| Type | Description |
|------|-------------|
| `shell` | Execute a shell command |
| `file.template` | Create a file from template content |
| `file.replace` | Replace content in an existing file |
| `json.patch` | Patch a JSON file |
| `yaml.patch` | Patch a YAML file |
| `python` | Execute Python code |

### Check Types

| Type | Description |
|------|-------------|
| `exit_code` | Verify step exit code |
| `file_exists` | Verify file exists |
| `file_contains` | Verify file contains string |
| `file_not_contains` | Verify file doesn't contain string |
| `dir_exists` | Verify directory exists |
| `custom` | Run custom Python check function |

## Fixtures

Fixtures are test cases for skills. Each fixture has:

- `input/` - Initial directory state (copied to sandbox)
- `expected/` - Expected final state (compared after run)
- `fixture.yaml` - Configuration overrides

### fixture.yaml

```yaml
# Override input values
inputs:
  message: "Custom message"

# Allow files not in expected/
allow_extra_files: true
```

## Examples

### Example 1: Create a deployment skill

```bash
# Record your deployment process
skillforge record --name deploy --workdir ./my-app

# In the recording shell:
[REC deploy] $ npm install
[REC deploy] $ npm run build
[REC deploy] $ rsync -av dist/ server:/var/www/
[REC deploy] $ exit

# Compile to a skill
skillforge compile rec_20240115_143022 --name deploy

# Test it
skillforge run ./skills/deploy --target ./my-app --dry-run
```

### Example 2: Import CI workflow

```bash
# Import your GitHub Actions workflow
skillforge import github-action .github/workflows/test.yml --out ./skills

# Review and edit
$EDITOR ./skills/test/skill.yaml

# Run locally
skillforge run ./skills/test --target .
```

### Example 3: Wrap existing script

```bash
# Wrap your build script
skillforge wrap ./scripts/build.sh --name build

# Add test fixtures
mkdir -p ./skills/build/fixtures/simple/input
mkdir -p ./skills/build/fixtures/simple/expected

# Create fixture input
echo '{"name": "test"}' > ./skills/build/fixtures/simple/input/package.json

# Run and bless
skillforge bless ./skills/build --fixture simple

# Now tests will pass
skillforge test ./skills/build
```

## Configuration

Configuration is stored in `~/.skillforge/config.yaml`:

```yaml
# Default output directory for new skills
default_skills_dir: ./skills

# Default shell for recording
default_shell: bash

# Sandbox settings
sandbox:
  cleanup: true
  base_dir: /tmp/skillforge
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run specific test file
pytest tests/test_runner.py -v

# Run with coverage
pytest tests/ --cov=skillforge
```

## License

MIT License - see LICENSE file for details.
