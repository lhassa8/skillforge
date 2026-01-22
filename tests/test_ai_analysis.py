"""Tests for AI-powered skill analysis."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from skillforge.ai import (
    analyze_skill,
    AnalysisResult,
    _parse_analysis_response,
)
from skillforge.scaffold import create_skill_scaffold
from skillforge.cli import app


runner = CliRunner()


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_skill(tmp_path: Path) -> Path:
    """Create a sample skill for testing."""
    skill_dir, _ = create_skill_scaffold(
        name="test-skill",
        output_dir=tmp_path,
        description="A test skill for analysis testing.",
    )
    return skill_dir


@pytest.fixture
def mock_analysis_response() -> str:
    """Sample analysis response from AI."""
    return json.dumps({
        "overall_score": 75,
        "clarity_score": 80,
        "completeness_score": 70,
        "examples_score": 72,
        "actionability_score": 78,
        "strengths": [
            "Clear description of purpose",
            "Good basic structure",
        ],
        "suggestions": [
            "Add more specific examples",
            "Include edge case handling",
        ],
        "issues": [
            "Missing error handling guidance",
        ],
    })


# =============================================================================
# _parse_analysis_response Tests
# =============================================================================


class TestParseAnalysisResponse:
    """Tests for _parse_analysis_response function."""

    def test_parse_clean_json(self):
        """Parse clean JSON response."""
        response = '{"overall_score": 80, "strengths": ["good"]}'
        result = _parse_analysis_response(response)
        assert result["overall_score"] == 80
        assert result["strengths"] == ["good"]

    def test_parse_json_with_code_block(self):
        """Parse JSON wrapped in markdown code block."""
        response = """```json
{"overall_score": 85, "suggestions": ["improve"]}
```"""
        result = _parse_analysis_response(response)
        assert result["overall_score"] == 85
        assert result["suggestions"] == ["improve"]

    def test_parse_json_with_plain_code_block(self):
        """Parse JSON wrapped in plain code block."""
        response = """```
{"overall_score": 90, "issues": []}
```"""
        result = _parse_analysis_response(response)
        assert result["overall_score"] == 90

    def test_parse_invalid_json_raises(self):
        """Invalid JSON raises exception."""
        with pytest.raises(json.JSONDecodeError):
            _parse_analysis_response("not valid json")


# =============================================================================
# analyze_skill Tests
# =============================================================================


class TestAnalyzeSkill:
    """Tests for analyze_skill function."""

    def test_analyze_nonexistent_skill(self, tmp_path: Path):
        """Analyzing nonexistent skill returns error."""
        result = analyze_skill(tmp_path / "nonexistent")
        assert result.success is False
        assert "Failed to load skill" in result.error

    def test_analyze_no_provider(self, sample_skill: Path):
        """Returns error when no provider available."""
        with patch("skillforge.ai.get_default_provider", return_value=None):
            result = analyze_skill(sample_skill)
            assert result.success is False
            assert "No AI provider available" in result.error

    def test_analyze_unknown_provider(self, sample_skill: Path):
        """Returns error for unknown provider."""
        result = analyze_skill(sample_skill, provider="unknown")
        assert result.success is False
        assert "Unknown provider" in result.error

    def test_analyze_with_anthropic(
        self, sample_skill: Path, mock_analysis_response: str
    ):
        """Analyze skill using Anthropic provider."""
        with patch("skillforge.ai._call_anthropic", return_value=mock_analysis_response):
            result = analyze_skill(sample_skill, provider="anthropic", model="test-model")

        assert result.success is True
        assert result.skill_name == "test-skill"
        assert result.overall_score == 75
        assert result.clarity_score == 80
        assert result.completeness_score == 70
        assert result.examples_score == 72
        assert result.actionability_score == 78
        assert len(result.strengths) == 2
        assert len(result.suggestions) == 2
        assert len(result.issues) == 1
        assert result.provider == "anthropic"
        assert result.model == "test-model"

    def test_analyze_with_openai(
        self, sample_skill: Path, mock_analysis_response: str
    ):
        """Analyze skill using OpenAI provider."""
        with patch("skillforge.ai._call_openai", return_value=mock_analysis_response):
            result = analyze_skill(sample_skill, provider="openai", model="gpt-4")

        assert result.success is True
        assert result.provider == "openai"
        assert result.model == "gpt-4"

    def test_analyze_with_ollama(
        self, sample_skill: Path, mock_analysis_response: str
    ):
        """Analyze skill using Ollama provider."""
        with patch("skillforge.ai._call_ollama", return_value=mock_analysis_response):
            result = analyze_skill(sample_skill, provider="ollama", model="llama3.2")

        assert result.success is True
        assert result.provider == "ollama"

    def test_analyze_api_error(self, sample_skill: Path):
        """API error returns failure result."""
        with patch("skillforge.ai._call_anthropic", side_effect=Exception("API error")):
            result = analyze_skill(sample_skill, provider="anthropic")

        assert result.success is False
        assert "API call failed" in result.error

    def test_analyze_parse_error(self, sample_skill: Path):
        """Invalid JSON response returns failure."""
        with patch("skillforge.ai._call_anthropic", return_value="not json"):
            result = analyze_skill(sample_skill, provider="anthropic")

        assert result.success is False
        assert "Failed to parse analysis response" in result.error


# =============================================================================
# AnalysisResult Tests
# =============================================================================


class TestAnalysisResult:
    """Tests for AnalysisResult dataclass."""

    def test_default_values(self):
        """Default values are set correctly."""
        result = AnalysisResult(success=True)
        assert result.success is True
        assert result.skill_name is None
        assert result.overall_score is None
        assert result.strengths == []
        assert result.suggestions == []
        assert result.issues == []

    def test_with_scores(self):
        """Scores are stored correctly."""
        result = AnalysisResult(
            success=True,
            overall_score=80,
            clarity_score=85,
            completeness_score=75,
            examples_score=70,
            actionability_score=90,
        )
        assert result.overall_score == 80
        assert result.clarity_score == 85
        assert result.completeness_score == 75
        assert result.examples_score == 70
        assert result.actionability_score == 90


# =============================================================================
# CLI Tests
# =============================================================================


class TestAnalyzeCLI:
    """Tests for analyze CLI command."""

    def test_analyze_nonexistent_skill(self):
        """CLI shows error for nonexistent skill."""
        result = runner.invoke(app, ["analyze", "/nonexistent/skill"])
        assert result.exit_code == 1
        assert "Error" in result.stdout

    def test_analyze_no_provider(self, sample_skill: Path):
        """CLI shows error when no provider available."""
        with patch("skillforge.ai.get_default_provider", return_value=None):
            result = runner.invoke(app, ["analyze", str(sample_skill)])

        assert result.exit_code == 1
        assert "No AI provider available" in result.stdout

    def test_analyze_success(
        self, sample_skill: Path, mock_analysis_response: str
    ):
        """CLI displays analysis results."""
        with patch("skillforge.ai._call_anthropic", return_value=mock_analysis_response):
            with patch("skillforge.ai.get_default_provider", return_value=("anthropic", "claude-test")):
                result = runner.invoke(app, ["analyze", str(sample_skill)])

        assert result.exit_code == 0
        assert "test-skill" in result.stdout
        assert "Overall Score" in result.stdout
        assert "75" in result.stdout
        assert "Clarity" in result.stdout
        assert "Strengths" in result.stdout
        assert "Suggestions" in result.stdout

    def test_analyze_json_output(
        self, sample_skill: Path, mock_analysis_response: str
    ):
        """CLI outputs valid JSON with --json flag."""
        with patch("skillforge.ai._call_anthropic", return_value=mock_analysis_response):
            with patch("skillforge.ai.get_default_provider", return_value=("anthropic", "claude-test")):
                result = runner.invoke(app, ["analyze", str(sample_skill), "--json"])

        assert result.exit_code == 0

        # Parse the JSON output
        data = json.loads(result.stdout)
        assert data["success"] is True
        assert data["skill_name"] == "test-skill"
        assert data["overall_score"] == 75
        assert "strengths" in data
        assert "suggestions" in data
        assert "issues" in data

    def test_analyze_json_error(self, sample_skill: Path):
        """CLI outputs JSON error with --json flag on failure."""
        with patch("skillforge.ai._call_anthropic", side_effect=Exception("API error")):
            result = runner.invoke(
                app,
                ["analyze", str(sample_skill), "--provider", "anthropic", "--json"],
            )

        assert result.exit_code == 1
        data = json.loads(result.stdout)
        assert data["success"] is False
        assert "error" in data

    def test_analyze_with_provider_option(
        self, sample_skill: Path, mock_analysis_response: str
    ):
        """CLI accepts --provider option."""
        with patch("skillforge.ai._call_openai", return_value=mock_analysis_response):
            result = runner.invoke(
                app,
                ["analyze", str(sample_skill), "--provider", "openai"],
            )

        assert result.exit_code == 0
        assert "openai" in result.stdout

    def test_analyze_with_model_option(
        self, sample_skill: Path, mock_analysis_response: str
    ):
        """CLI accepts --model option."""
        with patch("skillforge.ai._call_anthropic", return_value=mock_analysis_response):
            with patch("skillforge.ai.get_default_provider", return_value=("anthropic", "default")):
                result = runner.invoke(
                    app,
                    ["analyze", str(sample_skill), "--model", "claude-custom"],
                )

        assert result.exit_code == 0
        assert "claude-custom" in result.stdout
