"""Tests for AI-powered skill generation."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile

from skillforge.ai import (
    generate_skill,
    improve_skill,
    get_available_providers,
    get_default_provider,
    _extract_skill_content,
    _build_context,
    GenerationResult,
)


class TestExtractSkillContent:
    """Tests for extracting SKILL.md content from AI responses."""

    def test_extracts_clean_response(self):
        """Test extracting from a clean response."""
        raw = """---
name: test-skill
description: A test skill.
---

# Test Skill

Content here.
"""
        result = _extract_skill_content(raw)

        assert result.startswith("---")
        assert "name: test-skill" in result
        assert "# Test Skill" in result

    def test_handles_preamble_text(self):
        """Test extracting when there's text before the frontmatter."""
        raw = """Here's the SKILL.md content:

---
name: test-skill
description: A test skill.
---

# Test Skill
"""
        result = _extract_skill_content(raw)

        assert result.startswith("---")
        assert "name: test-skill" in result

    def test_handles_markdown_code_block(self):
        """Test extracting from markdown code block."""
        raw = """```markdown
---
name: test-skill
description: A test skill.
---

# Content
```"""
        # Should still find the --- markers
        result = _extract_skill_content(raw)
        assert "name: test-skill" in result


class TestBuildContext:
    """Tests for building context from directories."""

    def test_builds_context_from_readme(self):
        """Test that README is included in context."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            (path / "README.md").write_text("# My Project\n\nA test project.")

            context = _build_context(path)

            assert "README.md" in context
            assert "My Project" in context

    def test_builds_context_from_package_json(self):
        """Test that package.json is included in context."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            (path / "package.json").write_text('{"name": "test-package"}')

            context = _build_context(path)

            assert "package.json" in context
            assert "test-package" in context

    def test_includes_directory_structure(self):
        """Test that directory structure is included."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            (path / "src").mkdir()
            (path / "tests").mkdir()
            (path / "README.md").write_text("# Test")

            context = _build_context(path)

            assert "Directory Structure" in context

    def test_respects_max_size(self):
        """Test that context is limited in size."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            # Create a large file
            (path / "README.md").write_text("x" * 100000)

            context = _build_context(path, max_size=1000)

            assert len(context) < 100000


class TestGetAvailableProviders:
    """Tests for provider availability checking."""

    def test_returns_list(self):
        """Test that providers returns a list."""
        providers = get_available_providers()

        assert isinstance(providers, list)
        assert len(providers) >= 3  # anthropic, openai, ollama

    def test_includes_anthropic(self):
        """Test that Anthropic is listed."""
        providers = get_available_providers()
        names = [p["name"] for p in providers]

        assert "anthropic" in names

    def test_includes_openai(self):
        """Test that OpenAI is listed."""
        providers = get_available_providers()
        names = [p["name"] for p in providers]

        assert "openai" in names

    def test_includes_ollama(self):
        """Test that Ollama is listed."""
        providers = get_available_providers()
        names = [p["name"] for p in providers]

        assert "ollama" in names

    def test_provider_has_available_field(self):
        """Test that each provider has availability info."""
        providers = get_available_providers()

        for p in providers:
            assert "available" in p or "reason" in p


class TestGetDefaultProvider:
    """Tests for getting default provider."""

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    def test_returns_anthropic_when_available(self):
        """Test that Anthropic is preferred when available."""
        with patch("skillforge.ai.get_available_providers") as mock:
            mock.return_value = [
                {"name": "anthropic", "available": True, "default_model": "claude-sonnet-4-20250514"},
                {"name": "openai", "available": True, "default_model": "gpt-4o"},
            ]

            result = get_default_provider()

            assert result is not None
            assert result[0] == "anthropic"

    def test_returns_none_when_none_available(self):
        """Test that None is returned when no providers available."""
        with patch("skillforge.ai.get_available_providers") as mock:
            mock.return_value = [
                {"name": "anthropic", "available": False, "reason": "No key"},
                {"name": "openai", "available": False, "reason": "No key"},
                {"name": "ollama", "available": False, "reason": "Not running"},
            ]

            result = get_default_provider()

            assert result is None


class TestGenerateSkill:
    """Tests for skill generation."""

    def test_fails_when_no_provider(self):
        """Test that generation fails when no provider is available."""
        with patch("skillforge.ai.get_default_provider", return_value=None):
            result = generate_skill("Test description")

            assert not result.success
            assert "No AI provider" in result.error

    @patch("skillforge.ai._call_anthropic")
    def test_generates_with_anthropic(self, mock_call):
        """Test generation with Anthropic provider."""
        mock_call.return_value = """---
name: generated-skill
description: A generated skill. Use when testing.
---

# Generated Skill

Instructions here.
"""
        with patch("skillforge.ai.get_default_provider", return_value=("anthropic", "claude-sonnet-4-20250514")):
            result = generate_skill("Create a test skill")

            assert result.success
            assert result.skill is not None
            assert result.skill.name == "generated-skill"
            assert result.provider == "anthropic"

    @patch("skillforge.ai._call_anthropic")
    def test_uses_provided_name(self, mock_call):
        """Test that provided name is used."""
        mock_call.return_value = """---
name: ai-generated-name
description: A skill. Use when needed.
---

# Content
"""
        with patch("skillforge.ai.get_default_provider", return_value=("anthropic", "claude-sonnet-4-20250514")):
            result = generate_skill("Create a skill", name="my-custom-name")

            assert result.success
            assert result.skill.name == "my-custom-name"

    @patch("skillforge.ai._call_anthropic")
    def test_handles_api_error(self, mock_call):
        """Test handling of API errors."""
        mock_call.side_effect = Exception("API error")

        with patch("skillforge.ai.get_default_provider", return_value=("anthropic", "claude-sonnet-4-20250514")):
            result = generate_skill("Create a skill")

            assert not result.success
            assert "API call failed" in result.error

    @patch("skillforge.ai._call_anthropic")
    def test_handles_invalid_response(self, mock_call):
        """Test handling of unparseable response."""
        mock_call.return_value = "This is not valid SKILL.md content"

        with patch("skillforge.ai.get_default_provider", return_value=("anthropic", "claude-sonnet-4-20250514")):
            result = generate_skill("Create a skill")

            assert not result.success
            assert "Failed to parse" in result.error


class TestImproveSkill:
    """Tests for skill improvement."""

    def test_fails_on_missing_skill(self):
        """Test that improve fails when skill doesn't exist."""
        result = improve_skill(Path("/nonexistent/skill"), "Add examples")

        assert not result.success
        assert "Failed to load" in result.error

    @patch("skillforge.ai._call_anthropic")
    def test_improves_existing_skill(self, mock_call):
        """Test improving an existing skill."""
        mock_call.return_value = """---
name: improved-skill
description: An improved skill. Use when testing improvements.
---

# Improved Skill

Better instructions here with more examples.

## Example 1
...

## Example 2
...
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir)
            (skill_dir / "SKILL.md").write_text("""---
name: improved-skill
description: Original skill. Use when testing.
---

# Original Skill
""")

            with patch("skillforge.ai.get_default_provider", return_value=("anthropic", "claude-sonnet-4-20250514")):
                result = improve_skill(skill_dir, "Add more examples")

                assert result.success
                assert result.skill is not None
                assert "Example" in result.raw_content


class TestGenerationResult:
    """Tests for GenerationResult dataclass."""

    def test_success_result(self):
        """Test creating a success result."""
        from skillforge.skill import Skill

        skill = Skill(name="test", description="Test skill")
        result = GenerationResult(
            success=True,
            skill=skill,
            raw_content="---\nname: test\n---\n",
            provider="anthropic",
            model="claude-sonnet-4-20250514",
        )

        assert result.success
        assert result.skill.name == "test"
        assert result.error is None

    def test_failure_result(self):
        """Test creating a failure result."""
        result = GenerationResult(
            success=False,
            error="Something went wrong",
        )

        assert not result.success
        assert result.skill is None
        assert result.error == "Something went wrong"
