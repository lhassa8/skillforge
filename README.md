# SkillForge

[![PyPI version](https://badge.fury.io/py/ai-skillforge.svg)](https://pypi.org/project/ai-skillforge/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/lhassa8/skillforge/actions/workflows/tests.yml/badge.svg)](https://github.com/lhassa8/skillforge/actions/workflows/tests.yml)

**SkillForge** is the enterprise-grade platform for [Anthropic Agent Skills](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills) — custom instruction sets that extend Claude's capabilities for specific tasks.

**Create, validate, test, secure, version, and deploy skills across multiple AI platforms.**

```bash
# Generate a complete skill from a natural language description
skillforge generate "Review Python code for security vulnerabilities and best practices"

# Validate, test, and scan for security issues
skillforge validate ./skills/code-reviewer
skillforge test ./skills/code-reviewer
skillforge security scan ./skills/code-reviewer

# Deploy to Claude, OpenAI, or LangChain
skillforge publish ./skills/code-reviewer --platform claude
skillforge publish ./skills/code-reviewer --platform openai --mode gpt
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

SkillForge handles the entire skill development lifecycle: **generate → validate → test → secure → version → deploy**.

---

## Feature Highlights

| Feature | Description |
|---------|-------------|
| **AI Generation** | Generate production-ready skills from natural language descriptions |
| **Testing Framework** | Mock and live testing with assertions, regression baselines |
| **Versioning** | Semantic versioning, lock files, version constraints |
| **MCP Integration** | Expose skills as MCP tools, import tools from MCP servers |
| **Security Scanning** | Detect prompt injection, credential exposure, data exfiltration |
| **Governance** | Trust tiers, policies, audit trails for enterprise compliance |
| **Multi-Platform** | Deploy to Claude, OpenAI (Custom GPTs), LangChain Hub |
| **Analytics** | Usage tracking, cost analysis, ROI calculation |
| **Enterprise Config** | SSO, cloud storage, proxy support |

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

### Option 2: Start from a Template

Use built-in templates for common use cases:

```bash
# List available templates
skillforge templates

# Create from template
skillforge new my-reviewer --template code-review

# Preview a template before using
skillforge templates show code-review
```

**Available templates:**
| Template | Description |
|----------|-------------|
| `code-review` | Review code for best practices, bugs, security |
| `git-commit` | Write conventional commit messages |
| `git-pr` | Create comprehensive PR descriptions |
| `api-docs` | Generate API documentation |
| `debugging` | Systematic debugging assistance |
| `sql-helper` | Write and optimize SQL queries |
| `test-writer` | Generate unit tests |
| `explainer` | Explain complex code or concepts |

### Option 3: Manual Creation

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

# 7. Bundle for upload (for claude.ai)
skillforge bundle ./skills/security-reviewer

# OR: Install directly to Claude Code
skillforge install ./skills/security-reviewer
```

**Deploy options:**
- **Claude Code:** `skillforge install ./skills/my-skill` (skill is immediately available)
- **claude.ai:** Upload the `.zip` file at **Settings → Features → Upload Skill**

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
skillforge new my-skill --template code-review  # Start from template
```

#### `skillforge templates`

List and preview available skill templates.

```bash
# List all templates
skillforge templates

# Preview a specific template
skillforge templates show code-review
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

### Claude Code Commands

Install and manage skills directly in Claude Code.

#### `skillforge install`

Install a skill to Claude Code's skills directory.

```bash
# Install to user directory (~/.claude/skills/) - available in all projects
skillforge install ./skills/code-reviewer

# Install to project directory (./.claude/skills/) - project-specific
skillforge install ./skills/project-helper --project

# Overwrite existing installation
skillforge install ./skills/code-reviewer --force
```

#### `skillforge uninstall`

Remove a skill from Claude Code.

```bash
skillforge uninstall code-reviewer
skillforge uninstall project-helper --project
```

#### `skillforge sync`

Install all skills from a directory.

```bash
# Sync all skills to user directory
skillforge sync ./skills

# Sync to project directory
skillforge sync ./skills --project

# Force overwrite existing
skillforge sync ./skills --force
```

#### `skillforge installed`

List installed Claude Code skills.

```bash
# List all installed skills
skillforge installed

# Show only user-level skills
skillforge installed --user

# Show only project-level skills
skillforge installed --project

# Show installation paths
skillforge installed --paths
```

---

### Versioning Commands

Manage skill versions with semantic versioning support.

#### `skillforge version show`

Display the current version of a skill.

```bash
skillforge version show ./skills/my-skill
```

#### `skillforge version bump`

Increment the skill version.

```bash
# Bump patch version (1.0.0 -> 1.0.1)
skillforge version bump ./skills/my-skill

# Bump minor version (1.0.0 -> 1.1.0)
skillforge version bump ./skills/my-skill --minor

# Bump major version (1.0.0 -> 2.0.0)
skillforge version bump ./skills/my-skill --major

# Set a specific version
skillforge version bump ./skills/my-skill --set 2.0.0
```

#### `skillforge version list`

List available versions from registries.

```bash
skillforge version list code-reviewer
```

#### `skillforge lock`

Generate or verify lock files for reproducible installations.

```bash
# Generate lock file (skillforge.lock)
skillforge lock ./skills

# Verify installed skills match lock file
skillforge lock --check

# Install from lock file
skillforge pull code-reviewer --locked
```

**Lock file format (`skillforge.lock`):**
```yaml
version: "1"
skills:
  code-reviewer:
    version: "1.2.0"
    source: "https://github.com/skillforge/community-skills"
    checksum: "sha256:abc123..."
```

---

### MCP Commands

Integrate with the Model Context Protocol ecosystem.

#### `skillforge mcp init`

Create a new MCP server project.

```bash
skillforge mcp init ./my-mcp-server
skillforge mcp init ./my-server --name "My Tools" --description "Custom tools"
```

#### `skillforge mcp add`

Add a skill to an MCP server.

```bash
skillforge mcp add ./my-server ./skills/code-reviewer
```

#### `skillforge mcp remove`

Remove a tool from an MCP server.

```bash
skillforge mcp remove ./my-server code-reviewer
```

#### `skillforge mcp list`

List tools in an MCP server.

```bash
skillforge mcp list ./my-server
```

#### `skillforge mcp serve`

Run an MCP server (stdio transport for Claude Desktop).

```bash
skillforge mcp serve ./my-server
```

#### `skillforge mcp config`

Show Claude Desktop configuration snippet.

```bash
skillforge mcp config ./my-server
```

#### `skillforge mcp discover`

Discover tools from configured MCP servers.

```bash
# Auto-detect Claude Desktop config
skillforge mcp discover

# Use custom config file
skillforge mcp discover --config ./mcp-config.json
```

#### `skillforge mcp import`

Import an MCP tool as a SkillForge skill.

```bash
skillforge mcp import my-tool-name
skillforge mcp import my-tool --output ./skills
```

---

### Security Commands

Scan skills for security vulnerabilities.

#### `skillforge security scan`

Scan a skill for security issues.

```bash
# Basic scan
skillforge security scan ./skills/my-skill

# Filter by minimum severity
skillforge security scan ./skills/my-skill --min-severity medium

# JSON output for CI/CD
skillforge security scan ./skills/my-skill --format json

# Fail if issues found (for CI)
skillforge security scan ./skills/my-skill --fail-on-issues
```

**Detects:**
- Prompt injection attempts
- Jailbreak patterns
- Credential exposure (API keys, passwords, private keys)
- Data exfiltration patterns
- Unsafe URLs and code execution risks

#### `skillforge security patterns`

List available security patterns.

```bash
# List all patterns
skillforge security patterns

# Filter by severity
skillforge security patterns --severity critical

# Filter by type
skillforge security patterns --type prompt_injection
```

---

### Governance Commands

Enterprise governance for skill management.

#### `skillforge governance trust`

View or set skill trust tier.

```bash
# View trust status
skillforge governance trust ./skills/my-skill

# Set trust tier
skillforge governance trust ./skills/my-skill --set verified
skillforge governance trust ./skills/my-skill --set enterprise
```

**Trust tiers:** `untrusted`, `community`, `verified`, `enterprise`

#### `skillforge governance policy`

Manage governance policies.

```bash
# List all policies
skillforge governance policy list

# Show policy details
skillforge governance policy show production

# Create custom policy
skillforge governance policy create my-policy

# Check skill against policy
skillforge governance check ./skills/my-skill --policy production
```

**Built-in policies:**
| Policy | Min Trust | Max Risk | Approval |
|--------|-----------|----------|----------|
| `development` | untrusted | 100 | No |
| `staging` | community | 70 | No |
| `production` | verified | 30 | Yes |
| `enterprise` | enterprise | 10 | Yes |

#### `skillforge governance audit`

View audit trail of skill events.

```bash
# View recent events
skillforge governance audit

# Filter by skill
skillforge governance audit --skill my-skill

# Filter by date
skillforge governance audit --from 2026-01-01 --to 2026-01-31

# Filter by event type
skillforge governance audit --type security_scan

# Summary view
skillforge governance audit --summary
```

#### `skillforge governance approve`

Formally approve a skill for deployment.

```bash
skillforge governance approve ./skills/my-skill --tier enterprise
skillforge governance approve ./skills/my-skill --tier verified --notes "Reviewed by security team"
```

---

### Publishing Commands

Deploy skills to multiple AI platforms.

#### `skillforge publish`

Publish a skill to an AI platform.

```bash
# Publish to Claude (Claude Code installation)
skillforge publish ./skills/my-skill --platform claude

# Publish to Claude API
skillforge publish ./skills/my-skill --platform claude --mode api

# Publish as OpenAI Custom GPT
skillforge publish ./skills/my-skill --platform openai --mode gpt

# Publish to OpenAI Assistants API
skillforge publish ./skills/my-skill --platform openai --mode assistant

# Publish to LangChain Hub
skillforge publish ./skills/my-skill --platform langchain --mode hub

# Export as LangChain Python module
skillforge publish ./skills/my-skill --platform langchain --mode module

# Dry run (validate without publishing)
skillforge publish ./skills/my-skill --platform claude --dry-run

# Publish to all platforms
skillforge publish ./skills/my-skill --all
```

#### `skillforge platforms`

List available platforms and their capabilities.

```bash
skillforge platforms
```

---

### Analytics Commands

Track skill usage and calculate ROI.

#### `skillforge analytics show`

View skill usage metrics.

```bash
skillforge analytics show my-skill
skillforge analytics show my-skill --period 30d
```

#### `skillforge analytics roi`

Calculate return on investment.

```bash
skillforge analytics roi my-skill
skillforge analytics roi my-skill --hourly-rate 75 --time-saved 5
```

#### `skillforge analytics report`

Generate comprehensive usage report.

```bash
skillforge analytics report
skillforge analytics report --period 30d --format json
```

#### `skillforge analytics cost`

View cost breakdown by model.

```bash
skillforge analytics cost my-skill
skillforge analytics cost my-skill --period 7d
```

#### `skillforge analytics estimate`

Project future costs.

```bash
skillforge analytics estimate my-skill --daily 10
skillforge analytics estimate my-skill --monthly 500
```

---

### Configuration Commands

Manage SkillForge configuration.

#### `skillforge config show`

Display current configuration.

```bash
skillforge config show
skillforge config show --section auth
```

#### `skillforge config set`

Set a configuration value.

```bash
skillforge config set default_model gpt-4o
skillforge config set log_level debug
skillforge config set proxy.http_proxy http://proxy:8080
```

#### `skillforge config path`

Show configuration file locations.

```bash
skillforge config path
```

#### `skillforge config init`

Create a configuration file.

```bash
# Create user config (~/.config/skillforge/config.yml)
skillforge config init

# Create project config (./.skillforge.yml)
skillforge config init --project
```

**Environment variable overrides:**

All config values can be overridden with `SKILLFORGE_` prefix:

```bash
export SKILLFORGE_DEFAULT_MODEL=gpt-4o
export SKILLFORGE_LOG_LEVEL=debug
export SKILLFORGE_COLOR_OUTPUT=false
```

---

### Migration Commands

Upgrade skills from older formats.

#### `skillforge migrate check`

List skills needing migration.

```bash
skillforge migrate check ./skills
skillforge migrate check ./skills --recursive
```

#### `skillforge migrate run`

Migrate a skill to v1.0 format.

```bash
# Migrate single skill (creates backup automatically)
skillforge migrate run ./skills/my-skill

# Migrate without backup
skillforge migrate run ./skills/my-skill --no-backup

# Migrate entire directory
skillforge migrate run ./skills --recursive
```

#### `skillforge migrate preview`

Preview migration changes without applying.

```bash
skillforge migrate preview ./skills/my-skill
```

**Skill format versions:**
| Version | Characteristics |
|---------|-----------------|
| v0.1 | No version field, basic frontmatter |
| v0.9 | Has version field, no schema_version |
| v1.0 | Has schema_version, min_skillforge_version |

---

### Utility Commands

#### `skillforge doctor`

Check installation health and environment.

```bash
skillforge doctor
```

#### `skillforge info`

Show detailed SkillForge information.

```bash
skillforge info
```

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

### Regression Testing

Compare responses against recorded baselines to catch unintended changes.

```bash
# Record baseline responses
skillforge test ./skills/my-skill --record-baselines

# Run regression tests (compare against baselines)
skillforge test ./skills/my-skill --regression

# Adjust similarity threshold (default: 80%)
skillforge test ./skills/my-skill --regression --threshold 0.9
```

**Regression assertion type:**
```yaml
tests:
  - name: "consistent_output"
    input: "Review this code"
    assertions:
      - type: similar_to
        baseline: "baseline_response_name"
        threshold: 0.8
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

Use SkillForge as a Python library. For API stability, import from `skillforge.api`:

```python
from pathlib import Path
from skillforge.api import (
    # Core
    Skill,
    validate_skill,
    bundle_skill,

    # Testing
    run_tests,
    TestResult,

    # Security
    scan_skill,
    ScanResult,
    Severity,

    # Governance
    TrustTier,
    check_policy,

    # Platforms
    publish_skill,
    Platform,

    # Analytics
    record_success,
    get_skill_metrics,

    # Versioning
    SkillVersion,
    parse_version,
    bump_version,

    # MCP
    skill_to_mcp_tool,
    create_mcp_server,

    # Config
    get_config,
    SkillForgeConfig,
)
```

### Basic Usage

```python
from pathlib import Path
from skillforge import (
    generate_skill,
    validate_skill_directory,
    bundle_skill,
)

# Generate a skill
result = generate_skill(
    description="Help users write SQL queries",
    name="sql-helper",
    provider="anthropic",
)

if result.success:
    print(f"Generated: {result.skill.name}")

# Validate a skill directory
skill_path = Path("./skills/sql-helper")
validation = validate_skill_directory(skill_path)
if validation.valid:
    print("Skill is valid!")

# Bundle for deployment
bundle_result = bundle_skill(skill_path)
print(f"Bundle created: {bundle_result.output_path}")
```

### Security Scanning

```python
from skillforge.api import scan_skill, Severity

result = scan_skill(Path("./skills/my-skill"))

print(f"Risk score: {result.risk_score}/100")
print(f"Passed: {result.passed}")

for finding in result.findings:
    if finding.severity >= Severity.HIGH:
        print(f"[{finding.severity.name}] {finding.message}")
```

### Multi-Platform Publishing

```python
from skillforge.api import publish_skill, Platform

# Publish to Claude
result = publish_skill(
    Path("./skills/my-skill"),
    platform=Platform.CLAUDE,
    mode="code",
)

# Publish as OpenAI Custom GPT
result = publish_skill(
    Path("./skills/my-skill"),
    platform=Platform.OPENAI,
    mode="gpt",
)
```

### Analytics

```python
from skillforge.api import record_success, get_skill_metrics, calculate_roi

# Record a successful invocation
record_success(
    skill_name="code-reviewer",
    latency_ms=1500,
    input_tokens=100,
    output_tokens=500,
    model="claude-sonnet-4-20250514",
)

# Get metrics
metrics = get_skill_metrics("code-reviewer")
print(f"Total invocations: {metrics.total_invocations}")
print(f"Success rate: {metrics.success_rate:.1%}")

# Calculate ROI
roi = calculate_roi("code-reviewer", hourly_rate=75, minutes_saved=5)
print(f"ROI: {roi.roi_percentage:.0f}%")
```

### MCP Integration

```python
from skillforge.api import (
    skill_to_mcp_tool,
    create_mcp_server,
    Skill,
)

# Convert skill to MCP tool
skill = Skill.from_directory(Path("./skills/code-reviewer"))
mcp_tool = skill_to_mcp_tool(skill)

# Create MCP server
server = create_mcp_server(
    path=Path("./my-mcp-server"),
    name="My Tools",
)
```

> **Note:** Functions that work with files require `Path` objects, not strings.

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
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
- [Changelog](CHANGELOG.md)
- [Issue Tracker](https://github.com/lhassa8/skillforge/issues)

---

## Version

Current version: **1.0.0**

SkillForge follows [Semantic Versioning](https://semver.org/). The public API (exported from `skillforge.api`) is stable and will not have breaking changes in minor versions.

---

<p align="center">
  <strong>The enterprise platform for AI capability management.</strong>
</p>
