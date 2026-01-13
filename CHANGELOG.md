# Changelog

All notable changes to SkillForge will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/lhassa8/skillforge/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/lhassa8/skillforge/releases/tag/v0.1.0
