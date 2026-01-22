"""Tests for Claude Code integration."""

import pytest
from pathlib import Path
from unittest.mock import patch
from typer.testing import CliRunner

from skillforge.claude_code import (
    install_skill,
    uninstall_skill,
    list_installed_skills,
    sync_skills,
    is_skill_installed,
    get_skills_dir,
    InstallResult,
    InstalledSkill,
)
from skillforge.scaffold import create_skill_scaffold
from skillforge.cli import app


runner = CliRunner()


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_user_skills_dir(tmp_path: Path):
    """Mock the user skills directory."""
    user_dir = tmp_path / "user_skills"
    user_dir.mkdir()
    with patch("skillforge.claude_code.USER_SKILLS_DIR", user_dir):
        yield user_dir


@pytest.fixture
def mock_project_skills_dir(tmp_path: Path):
    """Mock the project skills directory."""
    project_dir = tmp_path / "project_skills"
    project_dir.mkdir()
    with patch("skillforge.claude_code.PROJECT_SKILLS_DIR", project_dir):
        yield project_dir


@pytest.fixture
def sample_skill(tmp_path: Path) -> Path:
    """Create a sample skill for testing."""
    skill_dir, _ = create_skill_scaffold(
        name="test-skill",
        output_dir=tmp_path,
        description="A test skill for unit testing.",
    )
    return skill_dir


@pytest.fixture
def multiple_skills(tmp_path: Path) -> Path:
    """Create multiple skills in a directory."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()

    for name in ["skill-one", "skill-two", "skill-three"]:
        create_skill_scaffold(
            name=name,
            output_dir=skills_dir,
            description=f"Description for {name}.",
        )

    return skills_dir


# =============================================================================
# get_skills_dir Tests
# =============================================================================


class TestGetSkillsDir:
    """Tests for get_skills_dir function."""

    def test_user_scope(self, mock_user_skills_dir: Path):
        """User scope returns user skills directory."""
        result = get_skills_dir("user")
        assert result == mock_user_skills_dir

    def test_project_scope(self, mock_project_skills_dir: Path):
        """Project scope returns project skills directory."""
        result = get_skills_dir("project")
        # Result should be resolved path
        assert result == mock_project_skills_dir.resolve()


# =============================================================================
# install_skill Tests
# =============================================================================


class TestInstallSkill:
    """Tests for install_skill function."""

    def test_install_to_user(
        self, sample_skill: Path, mock_user_skills_dir: Path
    ):
        """Install skill to user directory."""
        result = install_skill(sample_skill, scope="user")

        assert isinstance(result, InstallResult)
        assert result.skill_name == "test-skill"
        assert result.scope == "user"
        assert result.was_update is False
        assert (mock_user_skills_dir / "test-skill" / "SKILL.md").exists()

    def test_install_to_project(
        self, sample_skill: Path, mock_project_skills_dir: Path
    ):
        """Install skill to project directory."""
        result = install_skill(sample_skill, scope="project")

        assert result.scope == "project"
        assert (mock_project_skills_dir / "test-skill" / "SKILL.md").exists()

    def test_install_nonexistent_raises(self, mock_user_skills_dir: Path):
        """Installing nonexistent skill raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            install_skill(Path("/nonexistent/skill"), scope="user")

    def test_install_already_exists_raises(
        self, sample_skill: Path, mock_user_skills_dir: Path
    ):
        """Installing already installed skill raises FileExistsError."""
        install_skill(sample_skill, scope="user")

        with pytest.raises(FileExistsError):
            install_skill(sample_skill, scope="user")

    def test_install_force_overwrites(
        self, sample_skill: Path, mock_user_skills_dir: Path
    ):
        """Force flag allows overwriting existing installation."""
        install_skill(sample_skill, scope="user")
        result = install_skill(sample_skill, scope="user", force=True)

        assert result.was_update is True

    def test_install_invalid_skill_raises(
        self, tmp_path: Path, mock_user_skills_dir: Path
    ):
        """Installing invalid skill raises ValueError."""
        # Create invalid skill (missing SKILL.md)
        invalid_skill = tmp_path / "invalid"
        invalid_skill.mkdir()
        (invalid_skill / "README.md").write_text("Not a skill")

        with pytest.raises(ValueError):
            install_skill(invalid_skill, scope="user")


# =============================================================================
# uninstall_skill Tests
# =============================================================================


class TestUninstallSkill:
    """Tests for uninstall_skill function."""

    def test_uninstall_existing(
        self, sample_skill: Path, mock_user_skills_dir: Path
    ):
        """Uninstall an installed skill."""
        install_skill(sample_skill, scope="user")
        assert (mock_user_skills_dir / "test-skill").exists()

        removed = uninstall_skill("test-skill", scope="user")

        assert removed is not None
        assert not (mock_user_skills_dir / "test-skill").exists()

    def test_uninstall_nonexistent(self, mock_user_skills_dir: Path):
        """Uninstalling nonexistent skill returns None."""
        result = uninstall_skill("nonexistent", scope="user")
        assert result is None


# =============================================================================
# list_installed_skills Tests
# =============================================================================


class TestListInstalledSkills:
    """Tests for list_installed_skills function."""

    def test_list_empty(self, mock_user_skills_dir: Path):
        """List returns empty when no skills installed."""
        skills = list_installed_skills(scope="user")
        assert skills == []

    def test_list_installed(
        self, sample_skill: Path, mock_user_skills_dir: Path
    ):
        """List returns installed skills."""
        install_skill(sample_skill, scope="user")

        skills = list_installed_skills(scope="user")

        assert len(skills) == 1
        assert isinstance(skills[0], InstalledSkill)
        assert skills[0].name == "test-skill"
        assert skills[0].scope == "user"

    def test_list_both_scopes(
        self,
        sample_skill: Path,
        mock_user_skills_dir: Path,
        mock_project_skills_dir: Path,
    ):
        """List with no scope returns both user and project skills."""
        install_skill(sample_skill, scope="user")

        # Create another skill for project scope
        project_skill = sample_skill.parent / "project-skill"
        create_skill_scaffold(
            name="project-skill",
            output_dir=sample_skill.parent,
            description="Project skill.",
        )
        install_skill(sample_skill.parent / "project-skill", scope="project")

        skills = list_installed_skills(scope=None)

        assert len(skills) == 2
        scopes = {s.scope for s in skills}
        assert scopes == {"user", "project"}


# =============================================================================
# sync_skills Tests
# =============================================================================


class TestSyncSkills:
    """Tests for sync_skills function."""

    def test_sync_multiple(
        self, multiple_skills: Path, mock_user_skills_dir: Path
    ):
        """Sync installs all skills from directory."""
        installed, errors = sync_skills(multiple_skills, scope="user")

        assert len(installed) == 3
        assert len(errors) == 0

        for result in installed:
            assert (mock_user_skills_dir / result.skill_name / "SKILL.md").exists()

    def test_sync_skips_existing(
        self, multiple_skills: Path, mock_user_skills_dir: Path
    ):
        """Sync skips already installed skills."""
        # Install one first
        install_skill(multiple_skills / "skill-one", scope="user")

        installed, errors = sync_skills(multiple_skills, scope="user")

        assert len(installed) == 2
        assert len(errors) == 1
        assert errors[0][0] == "skill-one"

    def test_sync_force(
        self, multiple_skills: Path, mock_user_skills_dir: Path
    ):
        """Sync with force updates existing skills."""
        install_skill(multiple_skills / "skill-one", scope="user")

        installed, errors = sync_skills(multiple_skills, scope="user", force=True)

        assert len(installed) == 3
        assert len(errors) == 0

    def test_sync_nonexistent_raises(self, mock_user_skills_dir: Path):
        """Sync on nonexistent directory raises error."""
        with pytest.raises(FileNotFoundError):
            sync_skills(Path("/nonexistent"), scope="user")


# =============================================================================
# is_skill_installed Tests
# =============================================================================


class TestIsSkillInstalled:
    """Tests for is_skill_installed function."""

    def test_not_installed(self, mock_user_skills_dir: Path):
        """Returns False when skill not installed."""
        assert is_skill_installed("nonexistent", scope="user") is False

    def test_is_installed(
        self, sample_skill: Path, mock_user_skills_dir: Path
    ):
        """Returns True when skill is installed."""
        install_skill(sample_skill, scope="user")
        assert is_skill_installed("test-skill", scope="user") is True

    def test_checks_both_scopes(
        self,
        sample_skill: Path,
        mock_user_skills_dir: Path,
        mock_project_skills_dir: Path,
    ):
        """With no scope, checks both user and project."""
        install_skill(sample_skill, scope="project")

        assert is_skill_installed("test-skill", scope=None) is True
        assert is_skill_installed("test-skill", scope="user") is False
        assert is_skill_installed("test-skill", scope="project") is True


# =============================================================================
# CLI Tests
# =============================================================================


class TestInstallCLI:
    """Tests for install CLI command."""

    def test_install_command(
        self, sample_skill: Path, mock_user_skills_dir: Path
    ):
        """CLI install command works."""
        with patch("skillforge.claude_code.USER_SKILLS_DIR", mock_user_skills_dir):
            result = runner.invoke(app, ["install", str(sample_skill)])

        assert result.exit_code == 0
        assert "Installed" in result.stdout or "test-skill" in result.stdout

    def test_install_nonexistent(self):
        """CLI shows error for nonexistent skill."""
        result = runner.invoke(app, ["install", "/nonexistent/skill"])

        assert result.exit_code == 1
        assert "Error" in result.stdout


class TestInstalledCLI:
    """Tests for installed CLI command."""

    def test_installed_empty(self, mock_user_skills_dir: Path, mock_project_skills_dir: Path):
        """CLI shows message when no skills installed."""
        with patch("skillforge.claude_code.USER_SKILLS_DIR", mock_user_skills_dir):
            with patch("skillforge.claude_code.PROJECT_SKILLS_DIR", mock_project_skills_dir):
                result = runner.invoke(app, ["installed"])

        assert result.exit_code == 0
        assert "No skills installed" in result.stdout

    def test_installed_shows_skills(
        self, sample_skill: Path, mock_user_skills_dir: Path, mock_project_skills_dir: Path
    ):
        """CLI shows installed skills."""
        # Install a skill first
        with patch("skillforge.claude_code.USER_SKILLS_DIR", mock_user_skills_dir):
            install_skill(sample_skill, scope="user")

            with patch("skillforge.claude_code.PROJECT_SKILLS_DIR", mock_project_skills_dir):
                result = runner.invoke(app, ["installed"])

        assert result.exit_code == 0
        assert "test-skill" in result.stdout
