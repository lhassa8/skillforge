"""Tests for skill registry functionality."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from skillforge.registry import (
    add_registry,
    remove_registry,
    list_registries,
    update_registries,
    search_skills,
    pull_skill,
    get_skill_info,
    _load_config,
    _save_config,
    _github_url_to_raw,
    _extract_registry_name,
    Registry,
    SkillEntry,
    RegistryError,
    SkillNotFoundError,
    REGISTRIES_CONFIG,
)
from skillforge.cli import app


runner = CliRunner()


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_config_dir(tmp_path: Path, monkeypatch):
    """Mock the registries config location."""
    config_path = tmp_path / "config" / "skillforge" / "registries.json"
    monkeypatch.setattr("skillforge.registry.REGISTRIES_CONFIG", config_path)
    return config_path


@pytest.fixture
def sample_index() -> dict:
    """Sample registry index data."""
    return {
        "name": "test-registry",
        "description": "A test registry",
        "version": "1.0.0",
        "skills": [
            {
                "name": "code-reviewer",
                "description": "Review code for best practices",
                "version": "1.0.0",
                "repo": "https://github.com/user/code-reviewer",
                "author": "testuser",
                "tags": ["code", "review"],
                "updated": "2025-01-20",
            },
            {
                "name": "git-helper",
                "description": "Help with git operations",
                "version": "0.5.0",
                "repo": "https://github.com/user/git-helper",
                "author": "testuser",
                "tags": ["git", "vcs"],
                "updated": "2025-01-19",
            },
        ],
    }


@pytest.fixture
def mock_fetch_index(sample_index: dict):
    """Mock _fetch_index to return sample data."""
    with patch("skillforge.registry._fetch_index", return_value=sample_index):
        yield


# =============================================================================
# URL Conversion Tests
# =============================================================================


class TestGitHubUrlConversion:
    """Tests for GitHub URL conversion."""

    def test_basic_repo_url(self):
        """Convert basic GitHub repo URL."""
        url = "https://github.com/user/repo"
        result = _github_url_to_raw(url)
        assert result == "https://raw.githubusercontent.com/user/repo/main/index.json"

    def test_repo_with_branch(self):
        """Convert repo URL with branch."""
        url = "https://github.com/user/repo/tree/develop"
        result = _github_url_to_raw(url)
        assert result == "https://raw.githubusercontent.com/user/repo/develop/index.json"

    def test_trailing_slash(self):
        """Handle trailing slash."""
        url = "https://github.com/user/repo/"
        result = _github_url_to_raw(url)
        assert result == "https://raw.githubusercontent.com/user/repo/main/index.json"

    def test_invalid_url_raises(self):
        """Invalid URL raises error."""
        with pytest.raises(RegistryError):
            _github_url_to_raw("https://example.com/not-github")


class TestExtractRegistryName:
    """Tests for registry name extraction."""

    def test_extract_from_github_url(self):
        """Extract name from GitHub URL."""
        url = "https://github.com/skillforge/community-skills"
        assert _extract_registry_name(url) == "community-skills"

    def test_extract_with_trailing_slash(self):
        """Extract name with trailing slash."""
        url = "https://github.com/user/my-registry/"
        assert _extract_registry_name(url) == "my-registry"


# =============================================================================
# Config Tests
# =============================================================================


class TestConfig:
    """Tests for config loading/saving."""

    def test_load_empty_config(self, mock_config_dir: Path):
        """Load returns empty structure when no config exists."""
        config = _load_config()
        assert config == {"registries": [], "cache": {}}

    def test_save_and_load(self, mock_config_dir: Path):
        """Config can be saved and loaded."""
        config = {
            "registries": [{"name": "test", "url": "https://example.com"}],
            "cache": {},
        }
        _save_config(config)

        loaded = _load_config()
        assert loaded == config


# =============================================================================
# Registry Management Tests
# =============================================================================


class TestAddRegistry:
    """Tests for add_registry function."""

    def test_add_registry(self, mock_config_dir: Path, mock_fetch_index, sample_index):
        """Add a registry successfully."""
        registry = add_registry("https://github.com/user/test-registry")

        assert registry.name == "test-registry"
        assert len(registry.skills) == 2
        assert registry.skills[0].name == "code-reviewer"

    def test_add_registry_with_custom_name(
        self, mock_config_dir: Path, mock_fetch_index
    ):
        """Add registry with custom name."""
        registry = add_registry("https://github.com/user/repo", name="custom-name")
        assert registry.name == "custom-name"

    def test_add_duplicate_raises(self, mock_config_dir: Path, mock_fetch_index):
        """Adding duplicate registry raises error."""
        add_registry("https://github.com/user/test-registry")

        with pytest.raises(RegistryError, match="already exists"):
            add_registry("https://github.com/user/test-registry")

    def test_add_invalid_registry_raises(self, mock_config_dir: Path):
        """Adding registry with invalid index raises error."""
        with patch("skillforge.registry._fetch_index", return_value={}):
            with pytest.raises(RegistryError, match="missing 'skills'"):
                add_registry("https://github.com/user/invalid")


class TestRemoveRegistry:
    """Tests for remove_registry function."""

    def test_remove_existing(self, mock_config_dir: Path, mock_fetch_index):
        """Remove an existing registry."""
        add_registry("https://github.com/user/test-registry")
        assert remove_registry("test-registry") is True

        registries = list_registries()
        assert len(registries) == 0

    def test_remove_nonexistent(self, mock_config_dir: Path):
        """Remove nonexistent registry returns False."""
        assert remove_registry("nonexistent") is False


class TestListRegistries:
    """Tests for list_registries function."""

    def test_list_empty(self, mock_config_dir: Path):
        """List returns empty when no registries."""
        assert list_registries() == []

    def test_list_with_registries(self, mock_config_dir: Path, mock_fetch_index):
        """List returns configured registries."""
        add_registry("https://github.com/user/test-registry")

        registries = list_registries()

        assert len(registries) == 1
        assert registries[0].name == "test-registry"
        assert len(registries[0].skills) == 2


class TestUpdateRegistries:
    """Tests for update_registries function."""

    def test_update_refreshes_cache(self, mock_config_dir: Path, mock_fetch_index):
        """Update refreshes cached skill data."""
        add_registry("https://github.com/user/test-registry")

        # Modify the mock to return updated data
        updated_index = {
            "name": "test-registry",
            "description": "Updated description",
            "skills": [
                {
                    "name": "new-skill",
                    "description": "A new skill",
                    "version": "1.0.0",
                    "repo": "https://github.com/user/new-skill",
                }
            ],
        }

        with patch("skillforge.registry._fetch_index", return_value=updated_index):
            updated = update_registries()

        assert len(updated) == 1
        assert len(updated[0].skills) == 1
        assert updated[0].skills[0].name == "new-skill"


# =============================================================================
# Search Tests
# =============================================================================


class TestSearchSkills:
    """Tests for search_skills function."""

    def test_search_by_name(self, mock_config_dir: Path, mock_fetch_index):
        """Search finds skill by name."""
        add_registry("https://github.com/user/test-registry")

        results = search_skills("code-reviewer")

        assert len(results) == 1
        assert results[0].name == "code-reviewer"

    def test_search_by_description(self, mock_config_dir: Path, mock_fetch_index):
        """Search finds skill by description."""
        add_registry("https://github.com/user/test-registry")

        results = search_skills("git operations")

        assert len(results) == 1
        assert results[0].name == "git-helper"

    def test_search_by_tag(self, mock_config_dir: Path, mock_fetch_index):
        """Search finds skill by tag."""
        add_registry("https://github.com/user/test-registry")

        results = search_skills("review")

        assert len(results) == 1
        assert results[0].name == "code-reviewer"

    def test_search_multiple_terms(self, mock_config_dir: Path, mock_fetch_index):
        """Search with multiple terms."""
        add_registry("https://github.com/user/test-registry")

        results = search_skills("code best practices")

        assert len(results) == 1
        assert results[0].name == "code-reviewer"

    def test_search_no_results(self, mock_config_dir: Path, mock_fetch_index):
        """Search with no matches returns empty."""
        add_registry("https://github.com/user/test-registry")

        results = search_skills("nonexistent")

        assert len(results) == 0

    def test_search_specific_registry(self, mock_config_dir: Path, mock_fetch_index):
        """Search in specific registry."""
        add_registry("https://github.com/user/test-registry")

        results = search_skills("code", registry="test-registry")
        assert len(results) == 1

        results = search_skills("code", registry="nonexistent")
        assert len(results) == 0


# =============================================================================
# Get Skill Info Tests
# =============================================================================


class TestGetSkillInfo:
    """Tests for get_skill_info function."""

    def test_get_existing_skill(self, mock_config_dir: Path, mock_fetch_index):
        """Get info for existing skill."""
        add_registry("https://github.com/user/test-registry")

        skill = get_skill_info("code-reviewer")

        assert skill is not None
        assert skill.name == "code-reviewer"
        assert skill.version == "1.0.0"

    def test_get_nonexistent_skill(self, mock_config_dir: Path, mock_fetch_index):
        """Get info for nonexistent skill returns None."""
        add_registry("https://github.com/user/test-registry")

        skill = get_skill_info("nonexistent")

        assert skill is None


# =============================================================================
# Pull Skill Tests
# =============================================================================


class TestPullSkill:
    """Tests for pull_skill function."""

    def test_pull_not_found(self, mock_config_dir: Path, tmp_path: Path):
        """Pull nonexistent skill raises error."""
        with pytest.raises(SkillNotFoundError):
            pull_skill("nonexistent", tmp_path)

    def test_pull_no_repo(self, mock_config_dir: Path, mock_fetch_index, tmp_path: Path):
        """Pull skill with no repo raises error."""
        # Add registry with skill that has no repo
        index_no_repo = {
            "name": "test",
            "skills": [{"name": "no-repo", "description": "No repo", "version": "1.0.0", "repo": ""}],
        }
        with patch("skillforge.registry._fetch_index", return_value=index_no_repo):
            add_registry("https://github.com/user/test")

        with pytest.raises(RegistryError, match="no repository URL"):
            pull_skill("no-repo", tmp_path)

    def test_pull_already_exists(self, mock_config_dir: Path, mock_fetch_index, tmp_path: Path):
        """Pull to existing directory raises error."""
        add_registry("https://github.com/user/test-registry")

        # Create the output directory
        (tmp_path / "code-reviewer").mkdir()

        with pytest.raises(RegistryError, match="already exists"):
            pull_skill("code-reviewer", tmp_path)


# =============================================================================
# Dataclass Tests
# =============================================================================


class TestSkillEntry:
    """Tests for SkillEntry dataclass."""

    def test_default_values(self):
        """Default values are set correctly."""
        entry = SkillEntry(
            name="test",
            description="Test skill",
            version="1.0.0",
            repo="https://github.com/user/test",
        )

        assert entry.author == ""
        assert entry.tags == []
        assert entry.updated == ""
        assert entry.registry == ""


class TestRegistry:
    """Tests for Registry dataclass."""

    def test_default_values(self):
        """Default values are set correctly."""
        reg = Registry(name="test", url="https://example.com")

        assert reg.description == ""
        assert reg.skills == []
        assert reg.added == ""
        assert reg.fetched == ""


# =============================================================================
# CLI Tests
# =============================================================================


class TestRegistryCLI:
    """Tests for registry CLI commands."""

    def test_registry_list_empty(self, mock_config_dir: Path):
        """CLI shows message when no registries."""
        with patch("skillforge.registry.REGISTRIES_CONFIG", mock_config_dir):
            result = runner.invoke(app, ["registry", "list"])

        assert result.exit_code == 0
        assert "No registries configured" in result.stdout

    def test_registry_add(self, mock_config_dir: Path, mock_fetch_index):
        """CLI adds registry."""
        with patch("skillforge.registry.REGISTRIES_CONFIG", mock_config_dir):
            result = runner.invoke(
                app, ["registry", "add", "https://github.com/user/test-registry"]
            )

        assert result.exit_code == 0
        assert "Added registry" in result.stdout
        assert "test-registry" in result.stdout

    def test_registry_remove(self, mock_config_dir: Path, mock_fetch_index):
        """CLI removes registry."""
        with patch("skillforge.registry.REGISTRIES_CONFIG", mock_config_dir):
            # Add first
            runner.invoke(
                app, ["registry", "add", "https://github.com/user/test-registry"]
            )
            # Remove
            result = runner.invoke(app, ["registry", "remove", "test-registry"])

        assert result.exit_code == 0
        assert "Removed registry" in result.stdout


class TestSearchCLI:
    """Tests for search CLI command."""

    def test_search_no_registries(self, mock_config_dir: Path):
        """Search with no registries shows message."""
        with patch("skillforge.registry.REGISTRIES_CONFIG", mock_config_dir):
            result = runner.invoke(app, ["search", "test"])

        assert result.exit_code == 0
        assert "No registries configured" in result.stdout

    def test_search_with_results(self, mock_config_dir: Path, mock_fetch_index):
        """Search displays results."""
        with patch("skillforge.registry.REGISTRIES_CONFIG", mock_config_dir):
            runner.invoke(
                app, ["registry", "add", "https://github.com/user/test-registry"]
            )
            result = runner.invoke(app, ["search", "code"])

        assert result.exit_code == 0
        assert "code-reviewer" in result.stdout

    def test_search_no_results(self, mock_config_dir: Path, mock_fetch_index):
        """Search with no matches shows message."""
        with patch("skillforge.registry.REGISTRIES_CONFIG", mock_config_dir):
            runner.invoke(
                app, ["registry", "add", "https://github.com/user/test-registry"]
            )
            result = runner.invoke(app, ["search", "nonexistent"])

        assert result.exit_code == 0
        assert "No skills found" in result.stdout


class TestPullCLI:
    """Tests for pull CLI command."""

    def test_pull_not_found(self, mock_config_dir: Path, mock_fetch_index):
        """Pull nonexistent skill shows error."""
        with patch("skillforge.registry.REGISTRIES_CONFIG", mock_config_dir):
            runner.invoke(
                app, ["registry", "add", "https://github.com/user/test-registry"]
            )
            result = runner.invoke(app, ["pull", "nonexistent"])

        assert result.exit_code == 1
        assert "not found" in result.stdout
