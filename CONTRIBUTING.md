# Contributing to SkillForge

Thank you for your interest in contributing to SkillForge! This document provides guidelines and instructions for contributing.

## Code of Conduct

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md). Be respectful and constructive in all interactions.

## Getting Started

### Development Setup

```bash
# Clone the repository
git clone https://github.com/lhassa8/skillforge.git
cd skillforge

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows

# Install in development mode with all dependencies
pip install -e ".[dev,all]"

# Verify installation
skillforge doctor
pytest tests/ -v
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=skillforge --cov-report=html

# Run specific test file
pytest tests/test_skill.py -v

# Run tests matching a pattern
pytest tests/ -k "test_validate" -v
```

### Code Quality

We use the following tools to maintain code quality:

```bash
# Type checking
mypy skillforge/

# Linting
ruff check skillforge/

# Format check
ruff format --check skillforge/
```

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/lhassa8/skillforge/issues)
2. If not, create a new issue with:
   - Clear, descriptive title
   - Steps to reproduce
   - Expected vs actual behavior
   - Python version and OS
   - Relevant SKILL.md if applicable

### Suggesting Features

1. Check existing issues and discussions
2. Create a new issue with:
   - Clear description of the feature
   - Use case / motivation
   - Proposed implementation (optional)

### Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass: `pytest tests/ -v`
6. Run type checking: `mypy skillforge/`
7. Run linting: `ruff check skillforge/`
8. Commit with clear messages
9. Push and create a Pull Request

#### PR Guidelines

- Keep PRs focused on a single change
- Update documentation if needed
- Add tests for new features
- Follow existing code style
- Update CHANGELOG.md for user-facing changes

## Project Structure

```
skillforge/
├── skillforge/              # Main package
│   ├── __init__.py         # Package exports
│   ├── api.py              # Stable public API (v1.0.0)
│   ├── cli.py              # CLI entry point (Typer)
│   ├── skill.py            # Skill model and parsing
│   ├── validator.py        # Validation logic
│   ├── bundler.py          # Zip bundling/extraction
│   ├── scaffold.py         # Skill scaffolding
│   ├── composer.py         # Skill composition
│   ├── templates.py        # Built-in skill templates
│   ├── ai.py               # AI-powered generation
│   ├── tester.py           # Skill testing framework
│   ├── registry.py         # Skill registry management
│   ├── claude_code.py      # Claude Code integration
│   ├── versioning.py       # Semantic versioning
│   ├── lockfile.py         # Lock file management
│   ├── config.py           # Enterprise configuration
│   ├── migrate.py          # Migration tools
│   ├── mcp/                # MCP integration
│   │   ├── __init__.py
│   │   ├── mapping.py      # Skill <-> MCP tool conversion
│   │   ├── server.py       # MCP server generation
│   │   └── client.py       # MCP client/discovery
│   ├── security/           # Security scanning
│   │   ├── __init__.py
│   │   ├── scanner.py      # Security scanner
│   │   └── patterns.py     # Security patterns
│   ├── governance/         # Enterprise governance
│   │   ├── __init__.py
│   │   ├── trust.py        # Trust tiers
│   │   ├── policy.py       # Governance policies
│   │   └── audit.py        # Audit logging
│   ├── platforms/          # Multi-platform publishing
│   │   ├── __init__.py
│   │   ├── base.py         # Platform adapter base
│   │   ├── claude.py       # Claude adapter
│   │   ├── openai.py       # OpenAI adapter
│   │   └── langchain.py    # LangChain adapter
│   └── analytics/          # Usage analytics
│       ├── __init__.py
│       ├── tracker.py      # Usage tracking
│       └── reports.py      # ROI and reports
├── tests/                   # Test suite (700+ tests)
│   ├── test_skill.py
│   ├── test_validator.py
│   ├── test_bundler.py
│   ├── test_scaffold.py
│   ├── test_cli.py
│   ├── test_ai.py
│   ├── test_tester.py
│   ├── test_composer.py
│   ├── test_registry.py
│   ├── test_claude_code.py
│   ├── test_versioning.py
│   ├── test_lockfile.py
│   ├── test_mcp.py
│   ├── test_security.py
│   ├── test_governance.py
│   ├── test_platforms.py
│   ├── test_analytics.py
│   ├── test_config.py
│   └── test_migrate.py
├── examples/                # Examples and tutorials
│   ├── skills/             # Example skills
│   │   ├── code-reviewer/
│   │   ├── git-commit/
│   │   ├── api-documenter/
│   │   └── data-analyst/
│   └── tutorials/          # Step-by-step guides
└── skills/                  # Generated skills (gitignored)
```

## Testing Guidelines

- Write tests for all new functionality
- Use pytest fixtures for common setup
- Test both success and failure cases
- Use temporary directories for file operations
- Mock external services (AI providers, Vault, etc.)

### Test Structure

```python
class TestFeatureName:
    """Tests for feature description."""

    def test_success_case(self):
        """Test that feature works correctly."""
        ...

    def test_error_handling(self):
        """Test that errors are handled properly."""
        ...
```

## Documentation

- Update README.md for user-facing features
- Add docstrings to public functions
- Include examples in docstrings
- Update CHANGELOG.md for releases
- Update ROADMAP.md for planned features
- Add tutorials in `examples/tutorials/` for complex features

## Release Process

1. Update version in `pyproject.toml` and `skillforge/__init__.py`
2. Update CHANGELOG.md with release notes
3. Run full test suite: `pytest tests/ -v`
4. Commit changes: `git commit -m "vX.Y.Z: Release description"`
5. Create a git tag: `git tag vX.Y.Z`
6. Push commit and tag: `git push && git push origin vX.Y.Z`
7. Create GitHub release: `gh release create vX.Y.Z`
8. CI will build and publish to PyPI

### API Stability (v1.0.0+)

- All exports from `skillforge.api` are stable
- Breaking changes only in major versions
- Deprecated features get at least one minor version warning
- Use `@deprecated()` decorator for deprecations

## Questions?

- Open a [Discussion](https://github.com/lhassa8/skillforge/discussions)
- Check existing issues and documentation

Thank you for contributing!
