"""Tests for skillforge.platforms module."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from skillforge.platforms import (
    Platform,
    PlatformAdapter,
    PlatformCredentials,
    PublishError,
    PublishResult,
    TransformError,
    TransformResult,
    ClaudeAdapter,
    OpenAIAdapter,
    LangChainAdapter,
    get_adapter,
    get_platform,
    list_adapters,
    register_adapter,
    transform_skill,
    publish_skill,
    publish_to_all,
    preview_for_platform,
)
from skillforge.skill import Skill


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_skill():
    """Create a sample skill for testing."""
    return Skill(
        name="test-reviewer",
        description="A test code reviewer skill",
        content="Review the following code for issues:\n\n{code}\n\nProvide feedback.",
        version="1.0.0",
    )


@pytest.fixture
def skill_dir(sample_skill: Skill, tmp_path: Path):
    """Create a skill directory for testing."""
    skill_path = tmp_path / "test-reviewer"
    skill_path.mkdir()

    skill_md = skill_path / "SKILL.md"
    skill_md.write_text(f"""---
name: {sample_skill.name}
description: {sample_skill.description}
version: {sample_skill.version}
---

{sample_skill.content}
""")

    return skill_path


# =============================================================================
# Platform Enum Tests
# =============================================================================


class TestPlatform:
    """Tests for Platform enum."""

    def test_platform_values(self):
        """Test platform enum has expected values."""
        assert Platform.CLAUDE.value == "claude"
        assert Platform.OPENAI.value == "openai"
        assert Platform.LANGCHAIN.value == "langchain"

    def test_get_platform_by_name(self):
        """Test getting platform by name."""
        assert get_platform("claude") == Platform.CLAUDE
        assert get_platform("openai") == Platform.OPENAI
        assert get_platform("langchain") == Platform.LANGCHAIN

    def test_get_platform_case_insensitive(self):
        """Test platform lookup is case insensitive."""
        assert get_platform("CLAUDE") == Platform.CLAUDE
        assert get_platform("Claude") == Platform.CLAUDE
        assert get_platform("OpenAI") == Platform.OPENAI

    def test_get_platform_invalid(self):
        """Test getting invalid platform raises error."""
        with pytest.raises(ValueError, match="Unknown platform"):
            get_platform("invalid")


# =============================================================================
# Platform Registry Tests
# =============================================================================


class TestPlatformRegistry:
    """Tests for platform registry."""

    def test_list_adapters(self):
        """Test listing all registered adapters."""
        adapters = list_adapters()
        assert len(adapters) >= 3

        platforms = [a.platform for a in adapters]
        assert Platform.CLAUDE in platforms
        assert Platform.OPENAI in platforms
        assert Platform.LANGCHAIN in platforms

    def test_get_adapter_claude(self):
        """Test getting Claude adapter."""
        adapter = get_adapter(Platform.CLAUDE)
        assert isinstance(adapter, ClaudeAdapter)
        assert adapter.platform == Platform.CLAUDE

    def test_get_adapter_openai(self):
        """Test getting OpenAI adapter."""
        adapter = get_adapter(Platform.OPENAI)
        assert isinstance(adapter, OpenAIAdapter)
        assert adapter.platform == Platform.OPENAI

    def test_get_adapter_langchain(self):
        """Test getting LangChain adapter."""
        adapter = get_adapter(Platform.LANGCHAIN)
        assert isinstance(adapter, LangChainAdapter)
        assert adapter.platform == Platform.LANGCHAIN

    def test_get_adapter_by_platform_enum(self):
        """Test getting adapter by platform enum."""
        adapter = get_adapter(Platform.CLAUDE)
        assert isinstance(adapter, ClaudeAdapter)


# =============================================================================
# Claude Adapter Tests
# =============================================================================


class TestClaudeAdapter:
    """Tests for Claude adapter."""

    def test_platform_name(self):
        """Test platform name and description."""
        adapter = ClaudeAdapter()
        assert adapter.platform == Platform.CLAUDE
        assert "Claude" in adapter.platform_name
        assert "Anthropic" in adapter.platform_name

    def test_supported_features(self):
        """Test supported features."""
        adapter = ClaudeAdapter()
        features = adapter.supported_features
        assert isinstance(features, list)
        assert len(features) > 0

    def test_transform_skill(self, sample_skill: Skill):
        """Test transforming skill for Claude."""
        adapter = ClaudeAdapter()
        result = adapter.transform(sample_skill)

        assert isinstance(result, TransformResult)
        assert result.platform == Platform.CLAUDE
        assert result.skill_name == sample_skill.name
        assert "system_prompt" in result.content
        assert "project_knowledge" in result.content
        assert "claude_code" in result.content

    def test_transform_system_prompt_content(self, sample_skill: Skill):
        """Test system prompt contains skill content."""
        adapter = ClaudeAdapter()
        result = adapter.transform(sample_skill)

        system_prompt = result.content["system_prompt"]
        assert sample_skill.content in system_prompt

    def test_transform_project_knowledge(self, sample_skill: Skill):
        """Test project knowledge format."""
        adapter = ClaudeAdapter()
        result = adapter.transform(sample_skill)

        project = result.content["project_knowledge"]
        assert "title" in project
        assert "content" in project
        assert sample_skill.name in project["title"]

    def test_transform_claude_code(self, sample_skill: Skill):
        """Test Claude Code format."""
        adapter = ClaudeAdapter()
        result = adapter.transform(sample_skill)

        claude_code = result.content["claude_code"]
        assert sample_skill.name == claude_code["name"]
        assert sample_skill.content in claude_code["skill_md"]

    def test_publish_api_mode(self, sample_skill: Skill, tmp_path: Path):
        """Test publishing in API mode."""
        adapter = ClaudeAdapter()
        credentials = PlatformCredentials(
            platform=Platform.CLAUDE,
            api_key="sk-ant-test-key",
            extra={"mode": "api", "output_dir": str(tmp_path)},
        )

        result = adapter.publish(sample_skill, credentials)

        assert isinstance(result, PublishResult)
        assert result.platform == Platform.CLAUDE
        assert result.skill_name == sample_skill.name
        assert "output_file" in result.metadata

    def test_publish_dry_run(self, sample_skill: Skill, tmp_path: Path):
        """Test dry run doesn't create files."""
        adapter = ClaudeAdapter()
        credentials = PlatformCredentials(
            platform=Platform.CLAUDE,
            api_key="sk-ant-test-key",
            extra={"mode": "api", "output_dir": str(tmp_path)},
        )

        result = adapter.publish(sample_skill, credentials, dry_run=True)

        assert result.platform == Platform.CLAUDE
        # No files should be created in dry_run
        assert not list(tmp_path.glob("*.json"))

    def test_preview(self, sample_skill: Skill):
        """Test preview generation."""
        adapter = ClaudeAdapter()
        preview = adapter.preview(sample_skill)

        assert isinstance(preview, str)
        assert sample_skill.name in preview
        # Preview is JSON of transform content
        assert "system_prompt" in preview


# =============================================================================
# OpenAI Adapter Tests
# =============================================================================


class TestOpenAIAdapter:
    """Tests for OpenAI adapter."""

    def test_platform_name(self):
        """Test platform name and description."""
        adapter = OpenAIAdapter()
        assert adapter.platform == Platform.OPENAI
        assert "OpenAI" in adapter.platform_name
        # Description mentions GPT or Assistant or both
        desc = adapter.platform_description.lower()
        assert "gpt" in desc or "assistant" in desc

    def test_supported_features(self):
        """Test supported features."""
        adapter = OpenAIAdapter()
        features = adapter.supported_features
        assert isinstance(features, list)

    def test_transform_skill(self, sample_skill: Skill):
        """Test transforming skill for OpenAI."""
        adapter = OpenAIAdapter()
        result = adapter.transform(sample_skill)

        assert isinstance(result, TransformResult)
        assert result.platform == Platform.OPENAI
        assert "custom_gpt" in result.content
        assert "system_prompt" in result.content
        assert "assistant" in result.content

    def test_transform_custom_gpt(self, sample_skill: Skill):
        """Test Custom GPT configuration."""
        adapter = OpenAIAdapter()
        result = adapter.transform(sample_skill)

        gpt = result.content["custom_gpt"]
        assert "name" in gpt
        assert "description" in gpt
        assert "instructions" in gpt
        assert "conversation_starters" in gpt
        assert isinstance(gpt["conversation_starters"], list)

    def test_gpt_name_formatting(self, sample_skill: Skill):
        """Test GPT name is properly formatted."""
        adapter = OpenAIAdapter()
        result = adapter.transform(sample_skill)

        gpt = result.content["custom_gpt"]
        # Name should be title case without hyphens
        assert "-" not in gpt["name"]
        assert gpt["name"][0].isupper()

    def test_transform_system_prompt(self, sample_skill: Skill):
        """Test system prompt format."""
        adapter = OpenAIAdapter()
        result = adapter.transform(sample_skill)

        system_prompt = result.content["system_prompt"]
        assert isinstance(system_prompt, str)
        assert len(system_prompt) > 0

    def test_transform_assistant(self, sample_skill: Skill):
        """Test Assistant configuration."""
        adapter = OpenAIAdapter()
        result = adapter.transform(sample_skill)

        assistant = result.content["assistant"]
        assert "name" in assistant
        assert "instructions" in assistant
        assert "model" in assistant

    def test_publish_gpt_mode(self, sample_skill: Skill, tmp_path: Path):
        """Test publishing as Custom GPT."""
        adapter = OpenAIAdapter()
        credentials = PlatformCredentials(
            platform=Platform.OPENAI,
            api_key="",
            extra={"mode": "gpt", "output_dir": str(tmp_path)},
        )

        result = adapter.publish(sample_skill, credentials)

        assert result.platform == Platform.OPENAI
        assert "output_file" in result.metadata

    def test_publish_dry_run(self, sample_skill: Skill, tmp_path: Path):
        """Test dry run publishes without error."""
        adapter = OpenAIAdapter()
        credentials = PlatformCredentials(
            platform=Platform.OPENAI,
            api_key="",
            extra={"mode": "gpt", "output_dir": str(tmp_path)},
        )

        result = adapter.publish(sample_skill, credentials, dry_run=True)

        assert result.platform == Platform.OPENAI
        assert result.skill_name == sample_skill.name

    def test_preview(self, sample_skill: Skill):
        """Test preview generation."""
        adapter = OpenAIAdapter()
        preview = adapter.preview(sample_skill)

        assert isinstance(preview, str)
        # Preview is JSON of transform content
        assert "custom_gpt" in preview


# =============================================================================
# LangChain Adapter Tests
# =============================================================================


class TestLangChainAdapter:
    """Tests for LangChain adapter."""

    def test_platform_name(self):
        """Test platform name and description."""
        adapter = LangChainAdapter()
        assert adapter.platform == Platform.LANGCHAIN
        assert "LangChain" in adapter.platform_name
        # Description should mention prompt or template
        desc = adapter.platform_description.lower()
        assert "prompt" in desc or "template" in desc

    def test_supported_features(self):
        """Test supported features."""
        adapter = LangChainAdapter()
        features = adapter.supported_features
        assert isinstance(features, list)

    def test_transform_skill(self, sample_skill: Skill):
        """Test transforming skill for LangChain."""
        adapter = LangChainAdapter()
        result = adapter.transform(sample_skill)

        assert isinstance(result, TransformResult)
        assert result.platform == Platform.LANGCHAIN
        assert "prompt_template" in result.content
        assert "python_module" in result.content
        assert "hub_format" in result.content

    def test_transform_prompt_template(self, sample_skill: Skill):
        """Test prompt template generation."""
        adapter = LangChainAdapter()
        result = adapter.transform(sample_skill)

        template = result.content["prompt_template"]
        assert "template" in template
        assert "input_variables" in template
        assert isinstance(template["input_variables"], list)

    def test_variable_extraction(self, sample_skill: Skill):
        """Test variable extraction from skill content."""
        adapter = LangChainAdapter()
        result = adapter.transform(sample_skill)

        template = result.content["prompt_template"]
        # Variables are extracted from content
        assert isinstance(template["input_variables"], list)
        # At least one variable should be present (default 'input' if none found)
        assert len(template["input_variables"]) > 0

    def test_transform_python_module(self, sample_skill: Skill):
        """Test Python module generation."""
        adapter = LangChainAdapter()
        result = adapter.transform(sample_skill)

        module = result.content["python_module"]
        assert isinstance(module, str)
        assert "from langchain" in module
        assert "PromptTemplate" in module
        assert "def get_prompt" in module

    def test_transform_hub_format(self, sample_skill: Skill):
        """Test Hub format."""
        adapter = LangChainAdapter()
        result = adapter.transform(sample_skill)

        hub = result.content["hub_format"]
        assert "name" in hub
        assert "description" in hub
        assert "template" in hub

    def test_publish_module_mode(self, sample_skill: Skill, tmp_path: Path):
        """Test publishing as Python module."""
        adapter = LangChainAdapter()
        credentials = PlatformCredentials(
            platform=Platform.LANGCHAIN,
            api_key="",
            extra={"mode": "module", "output_dir": str(tmp_path)},
        )

        result = adapter.publish(sample_skill, credentials)

        assert result.platform == Platform.LANGCHAIN
        assert "output_file" in result.metadata

        # Verify file was created
        output_file = Path(result.metadata["output_file"])
        assert output_file.exists()
        assert output_file.suffix == ".py"

    def test_publish_json_mode(self, sample_skill: Skill, tmp_path: Path):
        """Test publishing as JSON."""
        adapter = LangChainAdapter()
        credentials = PlatformCredentials(
            platform=Platform.LANGCHAIN,
            api_key="",
            extra={"mode": "json", "output_dir": str(tmp_path)},
        )

        result = adapter.publish(sample_skill, credentials)

        output_file = Path(result.metadata["output_file"])
        assert output_file.suffix == ".json"

        # Verify valid JSON with expected structure
        content = json.loads(output_file.read_text())
        assert "prompt_template" in content
        assert "chat_prompt_template" in content

    def test_publish_dry_run(self, sample_skill: Skill, tmp_path: Path):
        """Test dry run publishes without error."""
        adapter = LangChainAdapter()
        credentials = PlatformCredentials(
            platform=Platform.LANGCHAIN,
            api_key="",
            extra={"mode": "module", "output_dir": str(tmp_path)},
        )

        result = adapter.publish(sample_skill, credentials, dry_run=True)

        assert result.platform == Platform.LANGCHAIN
        assert result.skill_name == sample_skill.name

    def test_preview(self, sample_skill: Skill):
        """Test preview generation."""
        adapter = LangChainAdapter()
        preview = adapter.preview(sample_skill)

        assert isinstance(preview, str)
        # Preview is JSON of transform content
        assert "prompt_template" in preview


# =============================================================================
# Convenience Function Tests
# =============================================================================


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_transform_skill_function(self, skill_dir: Path):
        """Test transform_skill convenience function."""
        result = transform_skill(skill_dir, Platform.CLAUDE)

        assert isinstance(result, TransformResult)
        assert result.platform == Platform.CLAUDE

    def test_publish_skill_function(self, skill_dir: Path, tmp_path: Path):
        """Test publish_skill convenience function."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = publish_skill(
            skill_dir,
            Platform.OPENAI,
            mode="gpt",
            output_dir=output_dir,
        )

        assert isinstance(result, PublishResult)
        assert result.platform == Platform.OPENAI

    def test_publish_to_all_function(self, skill_dir: Path, tmp_path: Path):
        """Test publish_to_all convenience function."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Use dry_run to avoid side effects like installing to user's system
        results = publish_to_all(skill_dir, output_dir=output_dir, dry_run=True)

        # publish_to_all returns results for all platforms, even if some fail
        assert isinstance(results, dict)
        # Should have results for all platforms
        assert len(results) == 3
        # At least OpenAI and LangChain should succeed
        assert Platform.OPENAI in results
        assert Platform.LANGCHAIN in results
        # All results should be PublishResult (or error results)
        for platform, result in results.items():
            assert isinstance(result, PublishResult)

    def test_preview_for_platform_function(self, skill_dir: Path):
        """Test preview_for_platform convenience function."""
        preview = preview_for_platform(skill_dir, Platform.OPENAI)

        assert isinstance(preview, str)
        assert len(preview) > 0


# =============================================================================
# Credentials Tests
# =============================================================================


class TestPlatformCredentials:
    """Tests for platform credentials."""

    def test_credentials_creation(self):
        """Test creating credentials."""
        creds = PlatformCredentials(
            platform=Platform.CLAUDE,
            api_key="test-key",
            extra={"mode": "api"},
        )

        assert creds.platform == Platform.CLAUDE
        assert creds.api_key == "test-key"
        assert creds.extra["mode"] == "api"

    def test_credentials_defaults(self):
        """Test credentials with defaults."""
        creds = PlatformCredentials(
            platform=Platform.OPENAI,
            api_key="",
        )

        assert creds.extra == {}


# =============================================================================
# Result Types Tests
# =============================================================================


class TestResultTypes:
    """Tests for result types."""

    def test_transform_result(self):
        """Test TransformResult creation."""
        result = TransformResult(
            platform=Platform.CLAUDE,
            skill_name="test-skill",
            transformed_name="test-skill",
            content={"key": "value"},
            metadata={"format": "json"},
        )

        assert result.platform == Platform.CLAUDE
        assert result.skill_name == "test-skill"
        assert result.content == {"key": "value"}

    def test_publish_result(self):
        """Test PublishResult creation."""
        result = PublishResult(
            platform=Platform.OPENAI,
            skill_name="test-skill",
            published_id="gpt-123",
            url="https://chat.openai.com/g/g-123",
            metadata={"mode": "gpt"},
        )

        assert result.platform == Platform.OPENAI
        assert result.published_id == "gpt-123"
        assert result.url == "https://chat.openai.com/g/g-123"


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Tests for error handling."""

    def test_transform_error(self):
        """Test TransformError."""
        with pytest.raises(TransformError):
            raise TransformError("Test error")

    def test_publish_error(self):
        """Test PublishError."""
        with pytest.raises(PublishError):
            raise PublishError("Test error")

    def test_invalid_platform_string(self):
        """Test getting platform from invalid string."""
        with pytest.raises(ValueError, match="Unknown platform"):
            get_platform("invalid_platform")
