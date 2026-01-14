# Contributing to SkillForge

Thank you for your interest in contributing to SkillForge! This document provides guidelines and instructions for contributing.

## Code of Conduct

Please be respectful and constructive in all interactions. We're building something together.

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
├── skillforge/           # Main package
│   ├── __init__.py      # Package exports
│   ├── cli.py           # CLI entry point (Typer)
│   ├── skill.py         # Skill model and parsing
│   ├── validator.py     # Validation logic
│   ├── bundler.py       # Zip bundling/extraction
│   ├── scaffold.py      # Skill scaffolding
│   └── ai.py            # AI-powered generation
├── tests/               # Test suite
│   ├── test_skill.py    # Skill model tests
│   ├── test_validator.py # Validation tests
│   ├── test_bundler.py  # Bundling tests
│   ├── test_scaffold.py # Scaffold tests
│   ├── test_cli.py      # CLI integration tests
│   └── test_ai.py       # AI generation tests
└── skills/              # Generated skills directory
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
- Update CHANGELOG.md

## Release Process

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Create a git tag: `git tag v0.x.0`
4. Push tag: `git push origin v0.x.0`
5. CI will build and publish to PyPI

## Questions?

- Open a [Discussion](https://github.com/lhassa8/skillforge/discussions)
- Check existing issues and documentation

Thank you for contributing!
