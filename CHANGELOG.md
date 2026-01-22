# Changelog

All notable changes to SkillForge will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.11.0] - 2026-01-22

### Added

- **Security Scanning** - Detect vulnerabilities in skills before deployment
  - Scan for prompt injection, jailbreak attempts, instruction overrides
  - Detect credential exposure (API keys, AWS keys, private keys, passwords)
  - Find data exfiltration patterns and unsafe URLs
  - Identify code execution risks and path traversal
  - Risk scoring (0-100) with severity levels (critical, high, medium, low, info)
  - 25+ built-in security patterns

- **Security CLI Commands**
  - `skillforge security scan ./skills/my-skill` - Scan skill for vulnerabilities
  - `skillforge security scan --min-severity medium` - Filter by severity
  - `skillforge security scan --format json` - JSON output for CI/CD
  - `skillforge security patterns` - List all security patterns
  - `skillforge security patterns --severity critical` - Filter patterns

- **Trust Tiers** - Classify skills by verification status
  - Four trust levels: untrusted, community, verified, enterprise
  - Trust metadata stored with skills (`.trust.yml`)
  - `skillforge governance trust ./skill` - View trust status
  - `skillforge governance trust ./skill --set verified` - Set trust tier

- **Governance Policies** - Control skill usage in different environments
  - Built-in policies: development, staging, production, enterprise
  - Configurable: min trust tier, max risk score, required scans, approval
  - `skillforge governance policy list` - List all policies
  - `skillforge governance policy show production` - View policy details
  - `skillforge governance policy create custom` - Create custom policy
  - `skillforge governance check ./skill --policy production` - Check against policy

- **Audit Trails** - Track skill lifecycle events
  - Log creation, modification, security scans, trust changes, approvals
  - Query events by skill, date range, event type
  - `skillforge governance audit` - View audit events
  - `skillforge governance audit --skill my-skill` - Filter by skill
  - `skillforge governance audit --summary` - View aggregate summary
  - `skillforge governance approve ./skill --tier enterprise` - Formal approval

- **Programmatic Security API**
  - `skillforge.security` module:
    - `scan_skill()`, `scan_content()`, `quick_scan()` functions
    - `SecurityScanner` class with configurable patterns
    - `ScanResult` with findings, risk score, pass/fail status
    - `SecurityPattern`, `SecurityFinding`, `Severity`, `SecurityIssueType`
    - `get_patterns_by_severity()`, `get_patterns_by_type()`

- **Programmatic Governance API**
  - `skillforge.governance.trust` module:
    - `TrustTier` enum, `TrustMetadata` dataclass
    - `get_trust_metadata()`, `set_trust_tier()`, `meets_trust_requirement()`
  - `skillforge.governance.policy` module:
    - `TrustPolicy`, `PolicyCheckResult`, `BUILTIN_POLICIES`
    - `check_policy()`, `enforce_policy()`, `load_policy()`, `save_policy()`
  - `skillforge.governance.audit` module:
    - `AuditLogger`, `AuditEvent`, `AuditQuery`, `AuditSummary`
    - `log_skill_created()`, `log_security_scan()`, `log_trust_changed()`
    - `log_policy_check()`, `log_approval()`, `query_events()`

## [0.10.0] - 2026-01-22

### Added

- **MCP Integration** - Connect SkillForge skills with the Model Context Protocol ecosystem
  - Bidirectional conversion between SkillForge skills and MCP tools
  - Generate MCP servers that expose skills as tools for Claude Desktop and other MCP clients
  - Discover and import tools from existing MCP servers as SkillForge skills

- **MCP Server Generation**
  - `skillforge mcp init ./my-server` - Create a new MCP server project
  - `skillforge mcp add ./my-server ./skills/my-skill` - Add a skill to the server
  - `skillforge mcp remove ./my-server tool-name` - Remove a tool from the server
  - `skillforge mcp list ./my-server` - List tools in a server
  - `skillforge mcp serve ./my-server` - Run the MCP server (stdio transport)
  - `skillforge mcp config ./my-server` - Show Claude Desktop configuration snippet

- **MCP Client / Discovery**
  - `skillforge mcp discover` - List tools from configured MCP servers
  - `skillforge mcp discover --config ./config.json` - Use custom config file
  - `skillforge mcp import <tool-name>` - Import an MCP tool as a skill
  - Auto-detects Claude Desktop config on macOS, Windows, and Linux

- **Programmatic MCP API**
  - `skillforge.mcp.mapping` module:
    - `MCPToolDefinition`, `MCPToolParameter` dataclasses
    - `skill_to_mcp_tool()` - Convert skill to MCP tool definition
    - `mcp_tool_to_skill()` - Convert MCP tool to skill
    - `parse_mcp_tool_response()` - Parse MCP server responses
    - `validate_tool_name()` - Validate MCP tool naming
  - `skillforge.mcp.server` module:
    - `MCPServerProject` - Full server project management
    - `MCPServerConfig` - Server configuration
    - `init_server()`, `load_server()`, `add_skill_to_server()`
    - `remove_tool_from_server()`, `list_server_tools()`, `run_server()`
    - `is_mcp_server()` - Check if path is MCP server project
  - `skillforge.mcp.client` module:
    - `DiscoveredTool`, `MCPServerInfo` dataclasses
    - `discover_tools_from_config()` - Query servers from config file
    - `discover_tools_from_server()` - Query a specific server
    - `import_tool_as_skill()`, `import_tool_by_name()` - Import tools
    - `get_claude_desktop_config_path()` - Get platform-specific config path
    - `list_configured_servers()` - List servers from config

## [0.9.0] - 2026-01-22

### Added

- **Skill Versioning** - Semantic versioning support for skills
  - Add `version` field to SKILL.md frontmatter
  - `skillforge version show ./skills/my-skill` - Display skill version
  - `skillforge version bump ./skills/my-skill` - Bump version (--major, --minor, --patch)
  - `skillforge version bump ./skills/my-skill --set 1.0.0` - Set specific version
  - `skillforge version list <skill-name>` - List available versions from registries

- **Lock Files** - Reproducible skill installations
  - `skillforge lock ./skills` - Generate `skillforge.lock` with checksums
  - `skillforge lock --check` - Verify installed skills match lock file
  - `skillforge pull <skill> --locked` - Install from lock file
  - SHA256 checksums ensure skill integrity

- **Version Constraints** - Flexible version requirements
  - Support for `^1.0.0` (caret), `~1.0.0` (tilde), `>=`, `<=`, `>`, `<`, `=` operators
  - `skillforge pull <skill> --version "^1.0.0"` - Pull with version constraint
  - Registry skills can list multiple available versions

- **Regression Testing** - Compare responses against baselines
  - `skillforge test ./skills/my-skill --record-baselines` - Record baseline responses
  - `skillforge test ./skills/my-skill --regression` - Compare against baselines
  - `--threshold 0.8` - Configure similarity threshold (default 80%)
  - New `similar_to` assertion type for fuzzy matching

- **Programmatic Versioning API**
  - `SkillVersion` dataclass for semantic versions
  - `VersionConstraint` for dependency resolution
  - `parse_version()`, `parse_constraint()`, `is_valid_version()`, `compare_versions()`
  - `SkillLockFile`, `LockedSkill` for lock file management
  - `generate_lock_file()`, `verify_against_lock()` functions
  - `record_baselines()`, `run_regression_tests()` for regression testing

### Changed

- `skillforge validate` now validates version format if specified
- `skillforge pull` supports `--version` and `--locked` options
- Registry `SkillEntry` includes `versions` field for available versions
- Skill model includes optional `version` field

## [0.8.0] - 2025-01-22

### Added

- **Skill Composition** - Combine multiple skills into composite skills
  - `skillforge compose ./skills/my-composite` - Compose a skill by resolving includes
  - `skillforge compose ./skills/my-composite --preview` - Preview composed skill without writing
  - `skillforge compose ./skills/my-composite --output ./skills/composed` - Write to specific directory
  - Add `includes` field to SKILL.md frontmatter to reference other skills
  - Circular dependency detection and prevention
  - Automatic composition before bundling for composite skills

- **Programmatic Composition API**
  - `compose_skill()` function for composing skills programmatically
  - `get_includes()`, `resolve_includes()` functions
  - `validate_composition()` for validating composite skills
  - `has_includes()` to check if a skill has includes
  - `CompositionResult`, `CompositionError`, `CircularDependencyError` classes

### Changed

- `skillforge validate` now validates includes for composite skills
- `skillforge preview` shows composed version for composite skills
- `skillforge bundle` auto-composes before bundling if skill has includes

## [0.7.0] - 2025-01-22

### Added

- **Skill Registry** - Discover and download skills from GitHub-based registries
  - `skillforge registry add <github-url>` - Add a skill registry
  - `skillforge registry list` - List configured registries
  - `skillforge registry remove <name>` - Remove a registry
  - `skillforge registry update` - Refresh all registry indexes
  - `skillforge search <query>` - Search for skills across registries
  - `skillforge pull <skill-name>` - Download a skill from a registry

- **Programmatic Registry API**
  - `add_registry()`, `remove_registry()`, `list_registries()`, `update_registries()` functions
  - `search_skills()`, `pull_skill()`, `get_skill_info()` functions
  - `Registry`, `SkillEntry` dataclasses
  - Config stored at `~/.config/skillforge/registries.json`

## [0.6.0] - 2025-01-21

### Added

- **AI-Powered Skill Analysis** - Analyze skills for quality and get improvement suggestions
  - `skillforge analyze ./skills/my-skill` - Get AI-powered quality analysis
  - `skillforge analyze ./skills/my-skill --json` - Output as JSON for CI/tooling
  - Quality scores: clarity, completeness, examples, actionability (0-100)
  - Detailed feedback: strengths, suggestions, issues

- **Programmatic Analysis API**
  - `analyze_skill()` function for programmatic analysis
  - `AnalysisResult` dataclass with scores and feedback

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
