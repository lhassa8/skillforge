"""Tests for the SkillForge CLI."""

from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from skillforge.cli import app
from skillforge import config

runner = CliRunner()


def test_app_help():
    """Test that the CLI shows help without errors."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "skillforge" in result.output.lower()


class TestInitCommand:
    """Tests for the init command."""

    def test_init_creates_config(self, tmp_path):
        """Test that init creates the configuration directory."""
        config_dir = tmp_path / ".skillforge"
        config_file = config_dir / "config.yaml"

        with patch.object(config, "CONFIG_DIR", config_dir):
            with patch.object(config, "CONFIG_FILE", config_file):
                with patch.object(config, "RECORDINGS_DIR", config_dir / "recordings"):
                    with patch.object(config, "LOGS_DIR", config_dir / "logs"):
                        with patch.object(config, "CACHE_DIR", config_dir / "cache"):
                            result = runner.invoke(app, ["init"])

        assert result.exit_code == 0
        assert "Initialized" in result.output
        assert config_dir.exists()
        assert config_file.exists()

    def test_init_warns_if_exists(self, tmp_path):
        """Test that init warns if config already exists."""
        config_dir = tmp_path / ".skillforge"
        config_dir.mkdir()
        config_file = config_dir / "config.yaml"
        config_file.write_text("default_shell: bash\n")

        with patch.object(config, "CONFIG_DIR", config_dir):
            with patch.object(config, "CONFIG_FILE", config_file):
                result = runner.invoke(app, ["init"])

        assert result.exit_code == 0
        assert "already exists" in result.output


class TestDoctorCommand:
    """Tests for the doctor command."""

    def test_doctor_runs_checks(self):
        """Test that doctor runs and displays check results."""
        result = runner.invoke(app, ["doctor"])
        # May exit with 0 or 1 depending on environment
        assert "Environment Check" in result.output
        assert "Python" in result.output
        assert "Git" in result.output

    def test_doctor_shows_table(self):
        """Test that doctor shows a formatted table."""
        result = runner.invoke(app, ["doctor"])
        assert "Check" in result.output
        assert "Status" in result.output

    def test_doctor_exits_with_error_on_failure(self):
        """Test that doctor exits with code 1 when checks fail."""
        from skillforge.doctor import CheckResult, CheckStatus

        failing_results = [
            CheckResult("Test", CheckStatus.ERROR, "Test failure"),
        ]

        with patch("skillforge.doctor.run_all_checks", return_value=failing_results):
            result = runner.invoke(app, ["doctor"])
            assert result.exit_code == 1


class TestNewCommand:
    """Tests for the new command."""

    def test_creates_skill_scaffold(self, tmp_path):
        """Test that new creates a skill scaffold."""
        result = runner.invoke(app, ["new", "my_skill", "--out", str(tmp_path)])

        assert result.exit_code == 0
        assert "Created skill scaffold" in result.output
        assert (tmp_path / "my_skill").exists()
        assert (tmp_path / "my_skill" / "skill.yaml").exists()
        assert (tmp_path / "my_skill" / "SKILL.txt").exists()
        assert (tmp_path / "my_skill" / "checks.py").exists()

    def test_creates_fixture_directories(self, tmp_path):
        """Test that new creates fixture directories."""
        runner.invoke(app, ["new", "my_skill", "--out", str(tmp_path)])

        assert (tmp_path / "my_skill" / "fixtures" / "happy_path" / "input").exists()
        assert (tmp_path / "my_skill" / "fixtures" / "happy_path" / "expected").exists()

    def test_shows_next_steps(self, tmp_path):
        """Test that new shows next steps."""
        result = runner.invoke(app, ["new", "my_skill", "--out", str(tmp_path)])

        assert "Next steps" in result.output
        assert "skill.yaml" in result.output

    def test_with_description(self, tmp_path):
        """Test that new accepts description option."""
        result = runner.invoke(
            app,
            ["new", "my_skill", "--out", str(tmp_path), "-d", "My custom description"],
        )

        assert result.exit_code == 0
        skill_txt = (tmp_path / "my_skill" / "SKILL.txt").read_text()
        assert "My custom description" in skill_txt

    def test_fails_if_exists(self, tmp_path):
        """Test that new fails if skill already exists."""
        runner.invoke(app, ["new", "my_skill", "--out", str(tmp_path)])
        result = runner.invoke(app, ["new", "my_skill", "--out", str(tmp_path)])

        assert result.exit_code == 1
        assert "already exists" in result.output

    def test_force_overwrites(self, tmp_path):
        """Test that --force overwrites existing skill."""
        runner.invoke(app, ["new", "my_skill", "--out", str(tmp_path)])
        result = runner.invoke(
            app, ["new", "my_skill", "--out", str(tmp_path), "--force"]
        )

        assert result.exit_code == 0
        assert "Created skill scaffold" in result.output

    def test_invalid_name_fails(self, tmp_path):
        """Test that invalid skill names fail."""
        result = runner.invoke(app, ["new", "", "--out", str(tmp_path)])

        assert result.exit_code == 1
        assert "Invalid skill name" in result.output


class TestLintCommand:
    """Tests for the lint command."""

    def test_lint_valid_skill(self, tmp_path):
        """Test linting a valid skill."""
        # Create a valid skill first
        runner.invoke(app, ["new", "test_skill", "--out", str(tmp_path)])

        result = runner.invoke(app, ["lint", str(tmp_path / "test_skill")])

        # Should have warnings (step without proper checks) but no errors
        assert "Linting skill" in result.output

    def test_lint_nonexistent_dir(self, tmp_path):
        """Test that linting non-existent directory fails."""
        result = runner.invoke(app, ["lint", str(tmp_path / "nonexistent")])

        assert result.exit_code == 1
        assert "Failed to load skill" in result.output

    def test_lint_shows_errors(self, tmp_path):
        """Test that lint shows errors for invalid skill."""
        import yaml

        skill_dir = tmp_path / "invalid_skill"
        skill_dir.mkdir()
        # Create invalid skill.yaml (missing required fields)
        (skill_dir / "skill.yaml").write_text(yaml.dump({"name": "test"}))

        result = runner.invoke(app, ["lint", str(skill_dir)])

        assert result.exit_code == 1
        assert "ERROR" in result.output

    def test_lint_shows_warnings(self, tmp_path):
        """Test that lint shows warnings."""
        import yaml

        skill_dir = tmp_path / "warn_skill"
        skill_dir.mkdir()
        (skill_dir / "fixtures").mkdir()
        (skill_dir / "fixtures" / "happy_path").mkdir()
        # Create skill with steps but no checks
        (skill_dir / "skill.yaml").write_text(yaml.dump({
            "name": "test",
            "inputs": [{"name": "target_dir", "type": "path"}],
            "steps": [{"id": "step1", "type": "shell", "command": "echo test"}],
        }))

        result = runner.invoke(app, ["lint", str(skill_dir)])

        assert "WARNING" in result.output


class TestOtherCommands:
    """Tests for other CLI commands (stubs)."""

    def test_cassette_subcommands_exist(self):
        """Test that cassette subcommands are registered."""
        result = runner.invoke(app, ["cassette", "--help"])
        assert result.exit_code == 0
        assert "record" in result.output
        assert "replay" in result.output

    def test_import_subcommands_exist(self):
        """Test that import subcommands are registered."""
        result = runner.invoke(app, ["import", "--help"])
        assert result.exit_code == 0
        assert "github-action" in result.output
