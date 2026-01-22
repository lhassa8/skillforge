# Changelog

All notable changes to SkillForge will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.0] - 2025-01-21

### Added

- **Claude Code Integration** - Install skills directly to Claude Code
  - `skillforge install ./skills/my-skill` - Install to user (~/.claude/skills/)
  - `skillforge install ./skills/my-skill --project` - Install to project (./.claude/skills/)
  - `skillforge uninstall my-skill` - Remove installed skill
  - `skillforge sync ./skills` - Install all skills from a directory
  - `skillforge installed` - List all installed skills

- **Programmatic Claude Code API**
  - `install_skill()`, `uninstall_skill()`, `list_installed_skills()` functions
  - `sync_skills()` for batch installation
  - `is_skill_installed()` to check installation status
  - `InstallResult`, `InstalledSkill` dataclasses

## [0.4.0] - 2025-01-21

### Added

- **Skill Templates** - Start skills from built-in templates
  - `skillforge new my-skill --template code-review` to create from template
  - `skillforge templates` to list all available templates
  - `skillforge templates show <name>` to preview a template
  - 8 built-in templates:
    - `code-review` - Review code for best practices, bugs, security
    - `git-commit` - Write conventional commit messages
    - `git-pr` - Create comprehensive PR descriptions
    - `api-docs` - Generate API documentation
    - `debugging` - Systematic debugging assistance
    - `sql-helper` - Write and optimize SQL queries
    - `test-writer` - Generate unit tests
    - `explainer` - Explain complex code or concepts

- **Programmatic Templates API**
  - `SkillTemplate` dataclass for template definitions
  - `get_template()`, `list_templates()`, `get_templates_by_category()` functions
  - Templates are organized by category (Code Quality, Git, Documentation, etc.)

## [0.3.0] - 2025-01-21

### Added

- **Skill Testing Framework** - Test your skills before deployment
  - `skillforge test` command with mock and live modes
  - YAML-based test definitions (`tests.yml` or `tests/*.test.yml`)
  - Multiple assertion types: `contains`, `not_contains`, `regex`, `starts_with`, `ends_with`, `length`, `json_valid`, `json_path`, `equals`
  - Mock mode for fast, free testing with pattern matching
  - Live mode for real API validation
  - Output formats: human-readable, JSON, JUnit XML (for CI)
  - Cost estimation for live mode (`--estimate-cost`)
  - Tag and name filtering (`--tags`, `--name`)
  - Stop on first failure (`--stop`)

- **Programmatic Testing API**
  - `TestCase`, `TestResult`, `TestSuiteResult` classes
  - `run_test_suite()`, `run_test_mock()`, `run_test_live()` functions
  - `load_test_suite()`, `discover_tests()` for test discovery
  - `evaluate_assertion()` for custom assertion evaluation
  - `estimate_live_cost()` for cost projections

## [0.2.2] - 2025-01-16

### Fixed

- Excluded `.claude/` directory from package builds (security fix)
- Added sdist exclusion rules in pyproject.toml for sensitive files

## [0.2.1] - 2025-01-14

### Added

- GitHub Actions CI workflow (Python 3.10-3.13 on Ubuntu and macOS)
- Security section in README

### Fixed

- Path traversal protection in zip extraction
- Symlinks excluded from bundles for security
- API key validation before provider calls
- Ruff and mypy linting errors
- Programmatic usage docs now show correct types (Path objects, result classes)

### Changed

- Package renamed from `skillforge` to `ai-skillforge` on PyPI
- Use `importlib.util.find_spec` for package detection instead of try/import

## [0.2.0] - 2025-01-13

### Changed

- **Complete Architecture Rebuild** - SkillForge is now focused on creating [Anthropic Agent Skills](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills), custom instructions that extend Claude's capabilities

### Added

- **SKILL.md Format Support**
  - YAML frontmatter with `name` and `description` fields
  - Validation against Anthropic requirements (name length, reserved words, etc.)
  - Support for additional markdown reference files
  - Support for executable scripts directory

- **New CLI Commands**
  - `skillforge new` - Create a new skill with SKILL.md scaffold
  - `skillforge validate` - Validate skill against Anthropic requirements
  - `skillforge bundle` - Package skill as zip for upload to claude.ai or API
  - `skillforge show` - Display skill details
  - `skillforge preview` - Preview how Claude will see the skill
  - `skillforge list` - List all skills in a directory
  - `skillforge init` - Initialize a directory for skill development
  - `skillforge add` - Add reference documents or scripts to a skill
  - `skillforge doctor` - Check environment for skill development

- **Core Modules**
  - `skill.py` - Skill model, SKILL.md parsing/generation
  - `validator.py` - Validation against Anthropic requirements
  - `bundler.py` - Zip packaging for upload
  - `scaffold.py` - SKILL.md scaffold generation

- **Programmatic API**
  - `Skill` class for working with skills programmatically
  - `validate_skill_directory()` and `validate_skill_md()` functions
  - `bundle_skill()` and `extract_skill()` functions
  - `create_skill_scaffold()`, `add_reference_doc()`, `add_script()` functions

### Removed

- Task automation framework (replaced with Anthropic Skills focus)
  - Sandbox execution system
  - Fixture-based testing
  - Cassette recording/replay
  - AI-powered skill generation
  - Skill registry system
  - Secret management
  - GitHub Actions import
  - Terminal session recording
  - Step types (shell, python, file.template, etc.)
  - Check types (exit_code, file_exists, etc.)

### Dependencies

- typer >= 0.9.0
- rich >= 13.0.0
- pyyaml >= 6.0

## [0.1.0] - 2024-01-15

### Added

- **Core Features**
  - Declarative YAML skill definitions with steps, inputs, and checks
  - Sandbox execution for safe skill testing
  - Fixture-based testing with expected output comparison
  - Golden artifact blessing for regression testing
  - Cassette recording for deterministic replay

- **Skill Creation**
  - `skillforge new` - Create skill scaffolds
  - `skillforge generate` - Generate from spec files
  - `skillforge wrap` - Wrap existing scripts
  - `skillforge import github-action` - Import GitHub Actions workflows
  - `skillforge record` / `skillforge compile` - Record terminal sessions

- **Skill Execution**
  - `skillforge run` - Execute skills with sandbox isolation
  - `skillforge lint` - Validate skill definitions
  - `skillforge test` - Run fixture tests
  - `skillforge bless` - Create golden artifacts

- **AI-Powered Generation**
  - `skillforge ai generate` - Generate skills from natural language
  - `skillforge ai refine` - Improve existing skills
  - `skillforge ai explain` - Explain what a skill does
  - Support for Anthropic Claude, OpenAI GPT, and Ollama

- **Skill Registry**
  - `skillforge registry add/remove/list/sync` - Manage registries
  - `skillforge search` - Search for skills
  - `skillforge install/uninstall` - Install skills from registries
  - `skillforge publish/pack` - Publish skills to registries
  - `skillforge update` - Update installed skills
  - Semantic versioning with flexible constraints

- **Secret Management**
  - `skillforge secret set/get/list/delete` - Manage secrets
  - Environment variable backend (`SKILLFORGE_SECRET_*`)
  - Encrypted file storage backend
  - HashiCorp Vault backend
  - `{secret:name}` placeholder syntax
  - Automatic log masking

- **Step Types**
  - `shell` - Execute shell commands
  - `python` - Run Python code
  - `file.template` - Create files from templates
  - `file.replace` - Replace content in files
  - `json.patch` - Patch JSON files
  - `yaml.patch` - Patch YAML files

- **Check Types**
  - `exit_code` - Verify step exit codes
  - `file_exists` - Verify file existence
  - `file_contains` / `file_not_contains` - Verify file content
  - `dir_exists` - Verify directory existence
  - `custom` - Run custom Python functions

- **Environment**
  - `skillforge init` - Initialize configuration
  - `skillforge doctor` - Verify environment setup

### Dependencies

- typer >= 0.9.0
- rich >= 13.0.0
- pyyaml >= 6.0

### Optional Dependencies

- `[ai]` - anthropic, openai for AI generation
- `[crypto]` - cryptography for Fernet encryption
- `[vault]` - hvac for HashiCorp Vault
- `[all]` - All optional dependencies

[Unreleased]: https://github.com/lhassa8/skillforge/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/lhassa8/skillforge/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/lhassa8/skillforge/releases/tag/v0.1.0
