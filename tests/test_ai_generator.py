"""Tests for AI-powered skill generation."""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from skillforge.ai_generator import (
    AIGeneratorError,
    AnthropicProvider,
    GenerationResult,
    LLMProvider,
    OllamaProvider,
    OpenAIProvider,
    ProjectContext,
    ProviderNotConfiguredError,
    analyze_project,
    build_explanation_prompt,
    build_generation_prompt,
    build_refinement_prompt,
    extract_yaml_from_response,
    generate_skill,
    get_provider,
    validate_generated_yaml,
)


# =============================================================================
# Project Context Analyzer Tests
# =============================================================================


class TestAnalyzeProject:
    """Tests for project context analyzer."""

    def test_empty_directory(self, tmp_path):
        """Test analyzing an empty directory."""
        ctx = analyze_project(tmp_path)
        assert ctx.project_type is None
        assert ctx.framework is None
        assert not ctx.has_git
        assert not ctx.has_docker
        assert not ctx.has_ci

    def test_nonexistent_directory(self, tmp_path):
        """Test analyzing a nonexistent directory."""
        ctx = analyze_project(tmp_path / "nonexistent")
        assert ctx.project_type is None

    def test_detect_python_pyproject(self, tmp_path):
        """Test detecting Python project with pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[project]
name = "test-project"
dependencies = ["fastapi", "uvicorn", "pydantic"]

[project.scripts]
serve = "app:main"
""")
        ctx = analyze_project(tmp_path)
        assert ctx.project_type == "python"
        assert ctx.build_tool == "pip/pyproject"
        assert "fastapi" in ctx.dependencies
        assert ctx.framework == "fastapi"

    def test_detect_python_requirements(self, tmp_path):
        """Test detecting Python project with requirements.txt."""
        reqs = tmp_path / "requirements.txt"
        reqs.write_text("""django>=4.0
djangorestframework
celery
redis
""")
        ctx = analyze_project(tmp_path)
        assert ctx.project_type == "python"
        assert ctx.build_tool == "pip"
        assert "django" in ctx.dependencies
        assert ctx.framework == "django"

    def test_detect_python_setuppy(self, tmp_path):
        """Test detecting Python project with setup.py."""
        (tmp_path / "setup.py").write_text("from setuptools import setup\nsetup()")
        ctx = analyze_project(tmp_path)
        assert ctx.project_type == "python"
        assert ctx.build_tool == "pip/setup.py"

    def test_detect_node_project(self, tmp_path):
        """Test detecting Node.js project."""
        package_json = tmp_path / "package.json"
        package_json.write_text(json.dumps({
            "name": "test-app",
            "dependencies": {
                "react": "^18.0.0",
                "react-dom": "^18.0.0",
            },
            "devDependencies": {
                "typescript": "^5.0.0",
            },
            "scripts": {
                "start": "react-scripts start",
                "build": "react-scripts build",
                "test": "react-scripts test",
            }
        }))
        ctx = analyze_project(tmp_path)
        assert ctx.project_type == "node"
        assert ctx.build_tool == "npm"
        assert "react" in ctx.dependencies
        assert ctx.framework == "react"
        assert "start" in ctx.scripts

    def test_detect_go_project(self, tmp_path):
        """Test detecting Go project."""
        (tmp_path / "go.mod").write_text("module example.com/test")
        ctx = analyze_project(tmp_path)
        assert ctx.project_type == "go"
        assert ctx.build_tool == "go"

    def test_detect_rust_project(self, tmp_path):
        """Test detecting Rust project."""
        (tmp_path / "Cargo.toml").write_text('[package]\nname = "test"')
        ctx = analyze_project(tmp_path)
        assert ctx.project_type == "rust"
        assert ctx.build_tool == "cargo"

    def test_detect_git(self, tmp_path):
        """Test detecting Git repository."""
        (tmp_path / ".git").mkdir()
        ctx = analyze_project(tmp_path)
        assert ctx.has_git

    def test_detect_docker(self, tmp_path):
        """Test detecting Docker configuration."""
        (tmp_path / "Dockerfile").write_text("FROM python:3.11")
        ctx = analyze_project(tmp_path)
        assert ctx.has_docker

    def test_detect_docker_compose(self, tmp_path):
        """Test detecting Docker Compose configuration."""
        (tmp_path / "docker-compose.yml").write_text("version: '3'")
        ctx = analyze_project(tmp_path)
        assert ctx.has_docker

    def test_detect_github_actions_ci(self, tmp_path):
        """Test detecting GitHub Actions CI."""
        workflows = tmp_path / ".github" / "workflows"
        workflows.mkdir(parents=True)
        (workflows / "ci.yml").write_text("name: CI")
        ctx = analyze_project(tmp_path)
        assert ctx.has_ci

    def test_detect_gitlab_ci(self, tmp_path):
        """Test detecting GitLab CI."""
        (tmp_path / ".gitlab-ci.yml").write_text("stages: [build]")
        ctx = analyze_project(tmp_path)
        assert ctx.has_ci

    def test_detect_jenkinsfile(self, tmp_path):
        """Test detecting Jenkins CI."""
        (tmp_path / "Jenkinsfile").write_text("pipeline {}")
        ctx = analyze_project(tmp_path)
        assert ctx.has_ci

    def test_existing_files_limited(self, tmp_path):
        """Test that existing files list is limited."""
        # Create many files
        for i in range(30):
            (tmp_path / f"file_{i}.txt").write_text("content")
        ctx = analyze_project(tmp_path)
        assert len(ctx.existing_files) <= 20

    def test_ignores_hidden_dirs_except_github(self, tmp_path):
        """Test that hidden directories are ignored except .github."""
        (tmp_path / ".hidden").mkdir()
        (tmp_path / ".github").mkdir()
        (tmp_path / "visible").mkdir()
        ctx = analyze_project(tmp_path)
        assert ".hidden/" not in ctx.existing_files
        # .github would only show if it has workflows


class TestProjectContextPrompt:
    """Tests for ProjectContext.to_prompt_context()."""

    def test_empty_context(self):
        """Test empty context produces minimal output."""
        ctx = ProjectContext()
        prompt = ctx.to_prompt_context()
        assert prompt == "No project context detected"

    def test_full_context(self):
        """Test full context produces expected output."""
        ctx = ProjectContext(
            project_type="python",
            framework="fastapi",
            build_tool="pip",
            has_git=True,
            has_docker=True,
            has_ci=True,
            dependencies=["fastapi", "uvicorn"],
            scripts={"serve": "python main.py"},
            existing_files=["main.py", "requirements.txt"],
        )
        prompt = ctx.to_prompt_context()
        assert "Project type: python" in prompt
        assert "Framework: fastapi" in prompt
        assert "Git" in prompt
        assert "Docker" in prompt
        assert "CI/CD" in prompt
        assert "fastapi" in prompt


# =============================================================================
# YAML Extraction Tests
# =============================================================================


class TestExtractYamlFromResponse:
    """Tests for YAML extraction from LLM responses."""

    def test_extract_yaml_block(self):
        """Test extracting YAML from markdown code block."""
        response = """Here's the skill:

```yaml
name: test_skill
version: "0.1.0"
steps:
  - id: step1
    type: shell
    command: echo hello
```

This skill does something."""
        yaml_content = extract_yaml_from_response(response)
        assert "name: test_skill" in yaml_content
        assert "echo hello" in yaml_content

    def test_extract_yml_block(self):
        """Test extracting YAML from ```yml block."""
        response = """```yml
name: test
version: "1.0"
```"""
        yaml_content = extract_yaml_from_response(response)
        assert "name: test" in yaml_content

    def test_extract_unmarked_yaml(self):
        """Test extracting YAML without code block markers."""
        response = """name: direct_yaml
version: "0.1.0"
steps:
  - id: step1
    type: shell

That's the skill."""
        yaml_content = extract_yaml_from_response(response)
        assert "name: direct_yaml" in yaml_content

    def test_extract_multiple_blocks_uses_first(self):
        """Test that first YAML block is used when multiple exist."""
        response = """```yaml
name: first
```
Some text
```yaml
name: second
```"""
        yaml_content = extract_yaml_from_response(response)
        assert "name: first" in yaml_content

    def test_no_yaml_raises_error(self):
        """Test that missing YAML raises error."""
        response = "This response has no YAML content at all."
        with pytest.raises(AIGeneratorError, match="No valid YAML"):
            extract_yaml_from_response(response)


# =============================================================================
# YAML Validation Tests
# =============================================================================


class TestValidateGeneratedYaml:
    """Tests for YAML validation."""

    def test_valid_minimal_yaml(self):
        """Test valid minimal skill YAML."""
        yaml_content = """
name: test_skill
steps:
  - id: step1
    type: shell
    command: echo hello
"""
        is_valid, errors = validate_generated_yaml(yaml_content)
        assert is_valid
        assert len(errors) == 0

    def test_valid_full_yaml(self):
        """Test valid full skill YAML."""
        yaml_content = """
name: full_skill
version: "0.1.0"
description: A test skill
inputs:
  - name: message
    type: string
steps:
  - id: step1
    type: shell
    command: echo {message}
checks:
  - id: check1
    type: file_exists
    path: "{sandbox_dir}/output.txt"
"""
        is_valid, errors = validate_generated_yaml(yaml_content)
        assert is_valid
        assert len(errors) == 0

    def test_invalid_yaml_syntax(self):
        """Test invalid YAML syntax."""
        yaml_content = """
name: test
steps:
  - id: step1
    type: shell
    command: echo hello
  invalid indentation here
"""
        is_valid, errors = validate_generated_yaml(yaml_content)
        assert not is_valid
        assert any("syntax" in e.lower() for e in errors)

    def test_missing_name(self):
        """Test missing name field."""
        yaml_content = """
steps:
  - id: step1
    type: shell
"""
        is_valid, errors = validate_generated_yaml(yaml_content)
        assert not is_valid
        assert any("name" in e.lower() for e in errors)

    def test_missing_steps(self):
        """Test missing steps field."""
        yaml_content = """
name: test_skill
"""
        is_valid, errors = validate_generated_yaml(yaml_content)
        assert not is_valid
        assert any("step" in e.lower() for e in errors)

    def test_empty_steps(self):
        """Test empty steps list."""
        yaml_content = """
name: test_skill
steps: []
"""
        is_valid, errors = validate_generated_yaml(yaml_content)
        assert not is_valid
        assert any("step" in e.lower() for e in errors)

    def test_step_missing_id(self):
        """Test step missing id field."""
        yaml_content = """
name: test
steps:
  - type: shell
    command: echo hello
"""
        is_valid, errors = validate_generated_yaml(yaml_content)
        assert not is_valid
        assert any("id" in e.lower() for e in errors)

    def test_step_missing_type(self):
        """Test step missing type field."""
        yaml_content = """
name: test
steps:
  - id: step1
    command: echo hello
"""
        is_valid, errors = validate_generated_yaml(yaml_content)
        assert not is_valid
        assert any("type" in e.lower() for e in errors)

    def test_check_missing_id(self):
        """Test check missing id field."""
        yaml_content = """
name: test
steps:
  - id: step1
    type: shell
    command: echo hello
checks:
  - type: file_exists
    path: "/tmp/file"
"""
        is_valid, errors = validate_generated_yaml(yaml_content)
        assert not is_valid
        assert any("check" in e.lower() and "id" in e.lower() for e in errors)

    def test_not_a_dict(self):
        """Test YAML that's not a dictionary."""
        yaml_content = "- item1\n- item2\n"
        is_valid, errors = validate_generated_yaml(yaml_content)
        assert not is_valid
        assert any("dictionary" in e.lower() for e in errors)


# =============================================================================
# Prompt Building Tests
# =============================================================================


class TestBuildGenerationPrompt:
    """Tests for generation prompt building."""

    def test_basic_prompt(self):
        """Test basic prompt without context."""
        prompt = build_generation_prompt("Create a deployment skill")
        assert "Create a deployment skill" in prompt
        assert "YAML" in prompt

    def test_prompt_with_context(self):
        """Test prompt with project context."""
        ctx = ProjectContext(
            project_type="python",
            framework="django",
            dependencies=["django", "celery"],
        )
        prompt = build_generation_prompt("Add caching", ctx)
        assert "Add caching" in prompt
        assert "python" in prompt.lower()
        assert "django" in prompt.lower()

    def test_prompt_with_requirements(self):
        """Test prompt with additional requirements."""
        prompt = build_generation_prompt(
            "Create CI",
            additional_requirements="Must support Python 3.10+"
        )
        assert "Create CI" in prompt
        assert "Python 3.10" in prompt


class TestBuildRefinementPrompt:
    """Tests for refinement prompt building."""

    def test_basic_refinement(self):
        """Test basic refinement prompt."""
        prompt = build_refinement_prompt(
            skill_yaml="name: test\nsteps: []",
            feedback="Add error handling",
        )
        assert "test" in prompt
        assert "error handling" in prompt.lower()

    def test_refinement_with_lint_errors(self):
        """Test refinement prompt with lint errors."""
        prompt = build_refinement_prompt(
            skill_yaml="name: test\nsteps: []",
            feedback="Fix issues",
            lint_errors=["Missing required field: steps", "Step 1 has no command"],
        )
        assert "Missing required field" in prompt
        assert "Step 1" in prompt


class TestBuildExplanationPrompt:
    """Tests for explanation prompt building."""

    def test_explanation_prompt(self):
        """Test explanation prompt."""
        prompt = build_explanation_prompt("name: test\nsteps:\n  - id: s1\n    type: shell")
        assert "Explain" in prompt
        assert "test" in prompt
        assert "shell" in prompt


# =============================================================================
# Provider Tests
# =============================================================================


class TestGetProvider:
    """Tests for provider factory."""

    def test_unknown_provider(self):
        """Test unknown provider raises error."""
        with pytest.raises(ProviderNotConfiguredError, match="Unknown provider"):
            get_provider("unknown_provider")

    def test_anthropic_no_key(self):
        """Test Anthropic without API key raises error."""
        with patch.dict(os.environ, {}, clear=True):
            # Ensure ANTHROPIC_API_KEY is not set
            env = os.environ.copy()
            env.pop("ANTHROPIC_API_KEY", None)
            with patch.dict(os.environ, env, clear=True):
                with pytest.raises(ProviderNotConfiguredError, match="ANTHROPIC_API_KEY"):
                    get_provider("anthropic")

    def test_openai_no_key(self):
        """Test OpenAI without API key raises error."""
        with patch.dict(os.environ, {}, clear=True):
            env = os.environ.copy()
            env.pop("OPENAI_API_KEY", None)
            with patch.dict(os.environ, env, clear=True):
                with pytest.raises(ProviderNotConfiguredError, match="OPENAI_API_KEY"):
                    get_provider("openai")

    def test_ollama_provider_created(self):
        """Test Ollama provider can be created without API key."""
        provider = get_provider("ollama")
        assert provider.name == "ollama"
        assert provider.model == "llama3.2"

    def test_ollama_custom_model(self):
        """Test Ollama with custom model."""
        provider = get_provider("ollama", model="codellama")
        assert provider.model == "codellama"


class TestAnthropicProvider:
    """Tests for Anthropic provider."""

    def test_init_with_key(self):
        """Test initialization with API key."""
        provider = AnthropicProvider(api_key="test-key")
        assert provider.name == "anthropic"
        assert "claude" in provider.model

    def test_init_from_env(self):
        """Test initialization from environment variable."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "env-key"}):
            provider = AnthropicProvider()
            assert provider.name == "anthropic"

    def test_custom_model(self):
        """Test custom model selection."""
        provider = AnthropicProvider(api_key="key", model="claude-3-haiku-20240307")
        assert provider.model == "claude-3-haiku-20240307"


class TestOpenAIProvider:
    """Tests for OpenAI provider."""

    def test_init_with_key(self):
        """Test initialization with API key."""
        provider = OpenAIProvider(api_key="test-key")
        assert provider.name == "openai"
        assert "gpt" in provider.model

    def test_custom_model(self):
        """Test custom model selection."""
        provider = OpenAIProvider(api_key="key", model="gpt-4-turbo")
        assert provider.model == "gpt-4-turbo"


class TestOllamaProvider:
    """Tests for Ollama provider."""

    def test_default_model(self):
        """Test default model."""
        provider = OllamaProvider()
        assert provider.model == "llama3.2"

    def test_custom_model(self):
        """Test custom model."""
        provider = OllamaProvider(model="codellama")
        assert provider.model == "codellama"

    def test_custom_host(self):
        """Test custom host."""
        provider = OllamaProvider(host="http://remote:11434")
        assert provider._host == "http://remote:11434"


# =============================================================================
# Skill Generation Tests (Mocked)
# =============================================================================


class MockProvider(LLMProvider):
    """Mock LLM provider for testing."""

    def __init__(self, response: str, tokens: int = 100):
        self._response = response
        self._tokens = tokens

    @property
    def name(self) -> str:
        return "mock"

    @property
    def model(self) -> str:
        return "mock-model"

    def generate(self, prompt: str, system_prompt: str) -> tuple[str, int]:
        return self._response, self._tokens


class TestGenerateSkill:
    """Tests for skill generation with mocked providers."""

    def test_generate_valid_skill(self, tmp_path):
        """Test generating a valid skill."""
        response = """```yaml
name: test_skill
version: "0.1.0"
description: A test skill
steps:
  - id: step1
    type: shell
    name: Say hello
    command: echo "hello world"
checks:
  - id: check1
    type: exit_code
    step_id: step1
    equals: 0
```"""
        provider = MockProvider(response)
        result = generate_skill(
            description="Create a hello world skill",
            output_dir=tmp_path,
            provider=provider,
        )

        assert result.success
        assert result.skill_dir is not None
        assert result.skill_dir.exists()
        assert (result.skill_dir / "skill.yaml").exists()
        assert (result.skill_dir / "SKILL.txt").exists()
        assert (result.skill_dir / "checks.py").exists()
        assert (result.skill_dir / "fixtures" / "happy_path").is_dir()

    def test_generate_invalid_yaml(self, tmp_path):
        """Test generating with invalid YAML response."""
        response = "This is not YAML at all, just plain text."
        provider = MockProvider(response)
        result = generate_skill(
            description="Create something",
            output_dir=tmp_path,
            provider=provider,
            auto_fix=False,
        )

        assert not result.success
        assert "No valid YAML" in result.error or result.error is not None

    def test_generate_missing_steps(self, tmp_path):
        """Test generating skill without steps."""
        response = """```yaml
name: incomplete_skill
version: "0.1.0"
```"""
        provider = MockProvider(response)
        result = generate_skill(
            description="Create something",
            output_dir=tmp_path,
            provider=provider,
            auto_fix=False,
        )

        assert not result.success
        assert result.error is not None

    def test_generate_with_context(self, tmp_path):
        """Test generating with project context."""
        # Create a Python project
        target = tmp_path / "project"
        target.mkdir()
        (target / "requirements.txt").write_text("flask\n")

        response = """```yaml
name: flask_setup
version: "0.1.0"
steps:
  - id: install
    type: shell
    command: pip install -r requirements.txt
```"""
        provider = MockProvider(response)
        output = tmp_path / "skills"
        result = generate_skill(
            description="Set up Flask",
            output_dir=output,
            provider=provider,
            target_dir=target,
        )

        assert result.success

    def test_generate_tokens_counted(self, tmp_path):
        """Test that tokens are counted."""
        response = """```yaml
name: test
steps:
  - id: s1
    type: shell
    command: echo hi
```"""
        provider = MockProvider(response, tokens=500)
        result = generate_skill(
            description="Test",
            output_dir=tmp_path,
            provider=provider,
        )

        assert result.success
        assert result.tokens_used == 500

    def test_generate_creates_gitkeep_files(self, tmp_path):
        """Test that .gitkeep files are created."""
        response = """```yaml
name: test
steps:
  - id: s1
    type: shell
    command: echo hi
```"""
        provider = MockProvider(response)
        result = generate_skill(
            description="Test",
            output_dir=tmp_path,
            provider=provider,
        )

        assert result.success
        assert (result.skill_dir / "fixtures" / "happy_path" / "input" / ".gitkeep").exists()
        assert (result.skill_dir / "cassettes" / ".gitkeep").exists()


# =============================================================================
# Integration Tests (require provider configuration)
# =============================================================================


def _can_use_ai_provider() -> bool:
    """Check if an AI provider is available and configured."""
    # Check Anthropic
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            import anthropic  # noqa: F401
            return True
        except ImportError:
            pass

    # Check OpenAI
    if os.environ.get("OPENAI_API_KEY"):
        try:
            import openai  # noqa: F401
            return True
        except ImportError:
            pass

    # Check Ollama (no package needed, just httpx)
    try:
        import httpx
        response = httpx.get("http://localhost:11434/api/tags", timeout=1.0)
        if response.status_code == 200:
            return True
    except Exception:
        pass

    return False


@pytest.mark.skipif(
    not _can_use_ai_provider(),
    reason="No AI provider available (need API key + package or running Ollama)"
)
class TestIntegrationWithRealProvider:
    """Integration tests that require a real provider."""

    def test_simple_generation(self, tmp_path):
        """Test simple skill generation with real provider."""
        result = generate_skill(
            description="Create a simple skill that echoes 'hello world'",
            output_dir=tmp_path,
        )

        assert result.success
        assert result.skill_dir.exists()

        # Verify generated skill is valid YAML
        skill_yaml = (result.skill_dir / "skill.yaml").read_text()
        data = yaml.safe_load(skill_yaml)
        assert "name" in data
        assert "steps" in data
