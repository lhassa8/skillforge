# Changelog

All notable changes to SkillForge will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
