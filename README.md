# SkillForge

[![PyPI version](https://badge.fury.io/py/ai-skillforge.svg)](https://pypi.org/project/ai-skillforge/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/lhassa8/skillforge/actions/workflows/tests.yml/badge.svg)](https://github.com/lhassa8/skillforge/actions/workflows/tests.yml)

**SkillForge** is the developer toolkit for [Anthropic Agent Skills](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills) — custom instruction sets that extend Claude's capabilities for specific tasks.

**Generate production-ready skills in seconds using AI, or craft them manually with validation and bundling tools.**

```bash
# Generate a complete skill from a natural language description
skillforge generate "Review Python code for security vulnerabilities and best practices"

# Validate, improve, and bundle for deployment
skillforge validate ./skills/code-reviewer
skillforge improve ./skills/code-reviewer "Add examples for async code patterns"
skillforge bundle ./skills/code-reviewer
```

---

## What Are Agent Skills?

Agent Skills are custom instructions that teach Claude how to handle specific tasks. When you upload a skill to Claude, it gains specialized knowledge and follows your defined workflows, examples, and guidelines.

**Use cases:**
- Code review with your team's standards
- Git commit message formatting
- API documentation generation
- Data analysis workflows
- Domain-specific assistants

SkillForge handles the entire skill development lifecycle: **generate → validate → test → improve → bundle → deploy**.

---

## Installation

### Basic Installation

```bash
pip install ai-skillforge
```

### With AI Generation (Recommended)

```bash
pip install ai-skillforge[ai]
```

This includes the Anthropic and OpenAI SDKs for AI-powered skill generation.

### Verify Installation

```bash
skillforge doctor     # Check installation health
skillforge providers  # Check available AI providers
```

---

## Quick Start

### Option 1: AI-Powered Generation (Fastest)

Generate a complete, production-ready skill from a description:

```bash
# Set your API key
export ANTHROPIC_API_KEY=your-key-here

# Generate the skill
skillforge generate "Help users write clear, conventional git commit messages"
```

**Output:**
```
✓ Generated skill: skills/git-commit-message-writer
  Provider: anthropic (claude-sonnet-4-20250514)
```

The generated skill includes:
- Proper YAML frontmatter
- Structured instructions
- Multiple realistic examples
- Edge case handling
- Best practices guidance

### Option 2: Manual Creation

Create a skill scaffold and customize it yourself:

```bash
# Create scaffold
skillforge new commit-helper -d "Help write git commit messages"

# Edit skills/commit-helper/SKILL.md with your instructions

# Validate and bundle
skillforge validate ./skills/commit-helper
skillforge bundle ./skills/commit-helper
```

---

## Complete Workflow Example

Here's the full workflow from idea to deployment:

```bash
# 1. Generate a skill
skillforge generate "Review Python code for security vulnerabilities" --name security-reviewer

# 2. Check the generated content
skillforge show ./skills/security-reviewer

# 3. Add tests (create tests.yml in the skill directory)
# See "Skill Testing" section for format

# 4. Run tests to verify behavior
skillforge test ./skills/security-reviewer

# 5. Improve it with AI (optional)
skillforge improve ./skills/security-reviewer "Add examples for Django and FastAPI"

# 6. Validate against Anthropic requirements
skillforge validate ./skills/security-reviewer

# 7. Bundle for upload
skillforge bundle ./skills/security-reviewer

# Output: skills/security-reviewer_20240115_143022.zip
```

**Deploy:** Upload the `.zip` file to Claude at **Settings → Features → Upload Skill**

---

## Commands Reference

### AI-Powered Commands

#### `skillforge generate`

Generate a complete skill using AI.

```bash
# Basic generation
skillforge generate "Analyze CSV data and generate insights"

# With custom name
skillforge generate "Debug JavaScript errors" --name js-debugger

# With project context (AI analyzes your codebase for relevant details)
skillforge generate "Help with this project's API" --context ./my-project

# Specify provider and model
skillforge generate "Write unit tests" --provider anthropic --model claude-sonnet-4-20250514

# Output to specific directory
skillforge generate "Format SQL queries" --out ./my-skills
```

**Options:**
| Option | Description |
|--------|-------------|
| `--name, -n` | Custom skill name (auto-generated if omitted) |
| `--out, -o` | Output directory (default: `./skills`) |
| `--context, -c` | Project directory to analyze for context |
| `--provider, -p` | AI provider: `anthropic`, `openai`, `ollama` |
| `--model, -m` | Specific model to use |
| `--force, -f` | Overwrite existing skill |

#### `skillforge improve`

Enhance an existing skill with AI assistance.

```bash
# Add more examples
skillforge improve ./skills/my-skill "Add 3 examples for error handling"

# Expand coverage
skillforge improve ./skills/my-skill "Add guidance for monorepo and squash merge scenarios"

# Restructure
skillforge improve ./skills/my-skill "Reorganize into clearer sections with a quick reference"

# Preview changes without saving
skillforge improve ./skills/my-skill "Simplify the instructions" --dry-run
```

#### `skillforge providers`

Check available AI providers and their status.

```bash
skillforge providers
```

**Supported Providers:**

| Provider | Setup | Default Model |
|----------|-------|---------------|
| Anthropic | `export ANTHROPIC_API_KEY=...` | claude-sonnet-4-20250514 |
| OpenAI | `export OPENAI_API_KEY=...` | gpt-4o |
| Ollama | `ollama serve` | llama3.2 |

---

### Core Commands

#### `skillforge new`

Create a new skill scaffold.

```bash
skillforge new my-skill -d "Description of what the skill does"
skillforge new my-skill --with-scripts  # Include scripts/ directory
```

#### `skillforge validate`

Validate a skill against Anthropic's requirements.

```bash
skillforge validate ./skills/my-skill
skillforge validate ./skills/my-skill --strict  # Treat warnings as errors
```

**Validates:**
- SKILL.md exists and has valid frontmatter
- Name format (lowercase, hyphens, no reserved words)
- Description length and content
- File size limits
- Required structure

#### `skillforge bundle`

Package a skill into a zip file for upload.

```bash
skillforge bundle ./skills/my-skill
skillforge bundle ./skills/my-skill -o custom-name.zip
```

#### `skillforge show`

Display skill metadata and content summary.

```bash
skillforge show ./skills/my-skill
```

#### `skillforge preview`

Preview how Claude will see the skill.

```bash
skillforge preview ./skills/my-skill
```

#### `skillforge list`

List all skills in a directory.

```bash
skillforge list ./skills
```

#### `skillforge add`

Add reference documents or scripts to a skill.

```bash
# Add a reference document
skillforge add ./skills/my-skill doc REFERENCE

# Add a script
skillforge add ./skills/my-skill script helper --language python
```

#### `skillforge doctor`

Check installation health and dependencies.

```bash
skillforge doctor
```

---

### Testing Commands

#### `skillforge test`

Test your skills before deployment. Supports mock mode (fast, free) and live mode (real API calls).

```bash
# Run tests in mock mode (default)
skillforge test ./skills/my-skill

# Run tests with real API calls
skillforge test ./skills/my-skill --mode live

# Filter tests by tags
skillforge test ./skills/my-skill --tags smoke,critical

# Filter tests by name
skillforge test ./skills/my-skill --name "basic_*"

# Output formats for CI/CD
skillforge test ./skills/my-skill --format json -o results.json
skillforge test ./skills/my-skill --format junit -o results.xml

# Estimate cost before running live tests
skillforge test ./skills/my-skill --mode live --estimate-cost

# Stop at first failure
skillforge test ./skills/my-skill --stop

# Verbose output with responses
skillforge test ./skills/my-skill -v
```

**Options:**
| Option | Description |
|--------|-------------|
| `--mode, -m` | Test mode: `mock` (default) or `live` |
| `--provider, -p` | AI provider for live mode |
| `--model` | Model to use for live mode |
| `--tags, -t` | Run only tests with these tags (comma-separated) |
| `--name, -n` | Run only tests matching these names |
| `--format, -f` | Output format: `human`, `json`, `junit` |
| `--output, -o` | Write results to file |
| `--verbose, -v` | Show detailed output including responses |
| `--estimate-cost` | Show cost estimate without running tests |
| `--stop, -s` | Stop at first failure |
| `--timeout` | Timeout per test in seconds (default: 30) |

---

## Skill Testing

Test your skills before deployment to catch issues early.

### Test File Location

Tests are defined in YAML files within your skill directory:

```
my-skill/
├── SKILL.md
├── tests.yml              # Option 1: Single test file
└── tests/                 # Option 2: Multiple test files
    ├── smoke.test.yml
    └── full.test.yml
```

### Test Definition Format

```yaml
version: "1.0"

defaults:
  timeout: 30

tests:
  - name: "basic_commit_request"
    description: "Tests basic commit message generation"
    input: "Help me write a commit message for adding user auth"
    assertions:
      - type: contains
        value: "feat"
      - type: regex
        pattern: "(feat|fix|docs):"
      - type: length
        min: 10
        max: 200
    trigger:
      should_trigger: true
    mock:
      response: |
        feat: add user authentication

        - Implement login/logout
        - Add session management
    tags: ["smoke", "basic"]

  - name: "handles_empty_input"
    description: "Should ask for clarification"
    input: "commit message"
    assertions:
      - type: contains
        value: "what changes"
        case_sensitive: false
    trigger:
      should_trigger: false
    mock:
      response: "What changes would you like me to describe?"
    tags: ["edge-case"]
```

### Assertion Types

| Type | Description | Example |
|------|-------------|---------|
| `contains` | Text is present | `value: "error"` |
| `not_contains` | Text is absent | `value: "exception"` |
| `regex` | Pattern matches | `pattern: "(feat\|fix):"` |
| `starts_with` | Response starts with | `value: "Here's"` |
| `ends_with` | Response ends with | `value: "."` |
| `length` | Length within bounds | `min: 10, max: 500` |
| `json_valid` | Valid JSON | (no params) |
| `json_path` | JSONPath value | `path: "$.status", value: "ok"` |
| `equals` | Exact match | `value: "expected text"` |

### Mock vs Live Mode

**Mock Mode** (default):
- Fast and free - no API calls
- Uses pattern matching for trigger detection
- Validates assertions against mock responses
- Great for rapid development and CI

**Live Mode** (`--mode live`):
- Makes real API calls
- Tests actual skill behavior
- Tracks token usage and cost
- Use for final validation before deployment

```bash
# Check cost before running
skillforge test ./skills/my-skill --mode live --estimate-cost

# Run live tests
skillforge test ./skills/my-skill --mode live
```

### CI/CD Integration

Use JUnit XML output for CI systems:

```bash
skillforge test ./skills/my-skill --format junit -o test-results.xml
```

**GitHub Actions example:**

```yaml
- name: Test skills
  run: |
    skillforge test ./skills/my-skill --format junit -o results.xml

- name: Upload test results
  uses: actions/upload-artifact@v3
  with:
    name: test-results
    path: results.xml
```

### Programmatic Testing

```python
from pathlib import Path
from skillforge import (
    load_test_suite,
    run_test_suite,
    TestSuiteResult,
)

# Load skill and tests
skill, suite = load_test_suite(Path("./skills/my-skill"))

# Run in mock mode
result: TestSuiteResult = run_test_suite(skill, suite, mode="mock")

print(f"Passed: {result.passed_tests}/{result.total_tests}")
print(f"Duration: {result.duration_ms:.1f}ms")

if not result.success:
    for test_result in result.test_results:
        if not test_result.passed:
            print(f"FAILED: {test_result.test_case.name}")
            for assertion in test_result.failed_assertions:
                print(f"  - {assertion.message}")
```

---

## Skill Anatomy

### Directory Structure

```
my-skill/
├── SKILL.md           # Required: Main skill definition
├── REFERENCE.md       # Optional: Additional context/documentation
├── GUIDELINES.md      # Optional: Style guides, standards
└── scripts/           # Optional: Executable scripts
    ├── helper.py
    └── utils.sh
```

### SKILL.md Format

Every skill requires a `SKILL.md` file with YAML frontmatter:

```markdown
---
name: code-reviewer
description: Use when asked to review code for bugs, security issues, or improvements. Provides structured feedback with severity levels and actionable suggestions.
---

# Code Reviewer

You are an expert code reviewer. Analyze code for bugs, security vulnerabilities, performance issues, and style improvements.

## Instructions

1. **Read the code** carefully and understand its purpose
2. **Identify issues** categorized by severity (Critical/High/Medium/Low)
3. **Provide fixes** with corrected code snippets
4. **Suggest improvements** for maintainability and performance

## Response Format

Structure your review as:
- **Summary**: One-line overview
- **Issues**: Categorized findings with severity
- **Recommendations**: Prioritized action items

## Examples

### Example 1: SQL Injection

**User request**: "Review this database function"
```python
def get_user(id):
    query = f"SELECT * FROM users WHERE id = {id}"
    return db.execute(query)
```

**Response**:
**Summary**: Critical SQL injection vulnerability found.

**Issues**:
- **Critical**: SQL injection via string interpolation

**Recommendation**:
```python
def get_user(id: int):
    query = "SELECT * FROM users WHERE id = %s"
    return db.execute(query, (id,))
```
```

### Frontmatter Requirements

| Field | Requirements |
|-------|-------------|
| `name` | Max 64 characters. Lowercase letters, numbers, hyphens only. Cannot contain "anthropic" or "claude". |
| `description` | Max 1024 characters. Explain **when** Claude should use this skill. Cannot contain XML tags. |

### Writing Effective Skills

**Do:**
- Be specific about when the skill applies
- Include realistic examples with input/output
- Cover edge cases and error scenarios
- Use consistent formatting
- Provide actionable instructions

**Don't:**
- Write vague or generic instructions
- Skip examples
- Assume context Claude won't have
- Include sensitive data or secrets

---

## Programmatic Usage

Use SkillForge as a Python library:

```python
from pathlib import Path
from skillforge import (
    generate_skill,
    improve_skill,
    validate_skill_directory,
    bundle_skill,
    GenerationResult,
    ValidationResult,
    BundleResult,
)

# Generate a skill (returns GenerationResult)
result: GenerationResult = generate_skill(
    description="Help users write SQL queries",
    name="sql-helper",          # Optional: overrides AI-generated name
    context_dir=Path("./src"),  # Optional: analyze project for context
    provider="anthropic",       # Optional: anthropic, openai, ollama
)

if result.success:
    print(f"Generated: {result.skill.name}")
    print(result.raw_content)

# Validate a skill directory (requires Path, returns ValidationResult)
skill_path = Path("./skills/sql-helper")
validation: ValidationResult = validate_skill_directory(skill_path)
if validation.valid:
    print("Skill is valid!")
else:
    for error in validation.errors:
        print(f"Error: {error}")

# Bundle for deployment (requires Path, returns BundleResult)
bundle_result: BundleResult = bundle_skill(skill_path)
print(f"Bundle created: {bundle_result.output_path}")
```

> **Note:** `validate_skill_directory()` and `bundle_skill()` require `Path` objects, not strings.

---

## Troubleshooting

### "No AI provider available"

```bash
# Check provider status
skillforge providers

# Ensure API key is set
export ANTHROPIC_API_KEY=your-key-here

# Or use OpenAI
export OPENAI_API_KEY=your-key-here

# Or start Ollama
ollama serve
```

### "anthropic package not installed"

```bash
pip install ai-skillforge[ai]
# or
pip install anthropic
```

### Validation Errors

| Error | Solution |
|-------|----------|
| "Name contains invalid characters" | Use only lowercase letters, numbers, and hyphens |
| "Name contains reserved word" | Remove "anthropic" or "claude" from name |
| "Description too long" | Keep under 1024 characters |
| "Missing SKILL.md" | Ensure SKILL.md exists in skill directory |

---

## Security

### API Keys

- Store API keys in environment variables, not in code or skill files
- Never commit `.env` files or API keys to version control
- Use separate API keys for development and production

```bash
# Set API key for current session only
export ANTHROPIC_API_KEY=your-key

# Or use a .env file (add to .gitignore)
echo "ANTHROPIC_API_KEY=your-key" >> .env
```

### Skill Content

- **Review generated skills** before deploying — AI-generated content should be verified
- **Never include secrets** in SKILL.md files (passwords, tokens, internal URLs)
- **Scripts are user-provided** — SkillForge does not execute scripts, but review them before use
- Skills uploaded to Claude have access to your conversations

### Bundle Security

- SkillForge validates zip files to prevent path traversal attacks
- Symlinks are excluded from bundles for security
- Maximum recommended bundle size: 10MB

---

## Development

### Setup

```bash
git clone https://github.com/lhassa8/skillforge.git
cd skillforge
pip install -e ".[dev]"
```

### Run Tests

```bash
pytest tests/ -v
pytest tests/ -v --cov=skillforge  # With coverage
```

### Code Quality

```bash
ruff check skillforge/
mypy skillforge/
```

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Resources

- [Anthropic Agent Skills Documentation](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills)
- [Changelog](CHANGELOG.md)
- [Issue Tracker](https://github.com/lhassa8/skillforge/issues)

---

<p align="center">
  <strong>Built for developers who want Claude to work the way they do.</strong>
</p>
