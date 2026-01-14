"""Tests for the SkillForge CLI."""

import pytest
from typer.testing import CliRunner

from skillforge.cli import app

runner = CliRunner()


def test_app_help():
    """Test that the CLI shows help without errors."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "skillforge" in result.output.lower()
    assert "Anthropic" in result.output


def test_app_no_args():
    """Test that CLI with no args shows help."""
    result = runner.invoke(app, [])
    assert "Usage" in result.output


class TestNewCommand:
    """Tests for the new command."""

    def test_creates_skill_directory(self, tmp_path):
        """Test that new creates a skill directory."""
        result = runner.invoke(app, ["new", "my-skill", "--out", str(tmp_path)])

        assert result.exit_code == 0
        assert "Created skill" in result.output
        assert (tmp_path / "my-skill").exists()

    def test_creates_skill_md(self, tmp_path):
        """Test that new creates SKILL.md."""
        runner.invoke(app, ["new", "test-skill", "--out", str(tmp_path)])

        assert (tmp_path / "test-skill" / "SKILL.md").exists()

    def test_shows_created_files(self, tmp_path):
        """Test that new shows created files."""
        result = runner.invoke(app, ["new", "my-skill", "--out", str(tmp_path)])

        assert "Created files" in result.output
        assert "SKILL.md" in result.output

    def test_shows_next_steps(self, tmp_path):
        """Test that new shows next steps."""
        result = runner.invoke(app, ["new", "my-skill", "--out", str(tmp_path)])

        assert "Next steps" in result.output
        assert "validate" in result.output
        assert "bundle" in result.output

    def test_with_description(self, tmp_path):
        """Test that new accepts description option."""
        result = runner.invoke(
            app,
            ["new", "my-skill", "--out", str(tmp_path), "-d", "My custom description"],
        )

        assert result.exit_code == 0
        skill_md = (tmp_path / "my-skill" / "SKILL.md").read_text()
        assert "My custom description" in skill_md

    def test_with_scripts(self, tmp_path):
        """Test that new creates scripts with --with-scripts."""
        result = runner.invoke(
            app,
            ["new", "script-skill", "--out", str(tmp_path), "--with-scripts"],
        )

        assert result.exit_code == 0
        assert (tmp_path / "script-skill" / "scripts").exists()
        assert (tmp_path / "script-skill" / "scripts" / "example.py").exists()

    def test_normalizes_name(self, tmp_path):
        """Test that new normalizes the skill name."""
        result = runner.invoke(app, ["new", "My Cool Skill", "--out", str(tmp_path)])

        assert result.exit_code == 0
        assert "Normalizing name" in result.output
        assert (tmp_path / "my-cool-skill").exists()

    def test_fails_if_exists(self, tmp_path):
        """Test that new fails if skill already exists."""
        runner.invoke(app, ["new", "my-skill", "--out", str(tmp_path)])
        result = runner.invoke(app, ["new", "my-skill", "--out", str(tmp_path)])

        assert result.exit_code == 1
        assert "already exists" in result.output
        assert "--force" in result.output

    def test_force_overwrites(self, tmp_path):
        """Test that --force overwrites existing skill."""
        runner.invoke(app, ["new", "my-skill", "--out", str(tmp_path)])
        result = runner.invoke(
            app, ["new", "my-skill", "--out", str(tmp_path), "--force"]
        )

        assert result.exit_code == 0
        assert "Created skill" in result.output


class TestValidateCommand:
    """Tests for the validate command."""

    def test_validate_valid_skill(self, tmp_path):
        """Test validating a valid skill."""
        runner.invoke(app, [
            "new", "valid-skill", "--out", str(tmp_path),
            "-d", "A valid skill. Use when testing validation."
        ])

        result = runner.invoke(app, ["validate", str(tmp_path / "valid-skill")])

        assert "Skill is valid" in result.output

    def test_validate_shows_skill_info(self, tmp_path):
        """Test that validate shows skill info."""
        runner.invoke(app, [
            "new", "info-skill", "--out", str(tmp_path),
            "-d", "Description for info testing."
        ])

        result = runner.invoke(app, ["validate", str(tmp_path / "info-skill")])

        assert "info-skill" in result.output
        assert "Description" in result.output

    def test_validate_shows_warnings(self, tmp_path):
        """Test that validate shows warnings."""
        runner.invoke(app, ["new", "warn-skill", "--out", str(tmp_path)])

        result = runner.invoke(app, ["validate", str(tmp_path / "warn-skill")])

        # Default skill has TODO and placeholder warnings
        assert "Warning" in result.output

    def test_validate_strict_fails_on_warnings(self, tmp_path):
        """Test that --strict fails on warnings."""
        runner.invoke(app, ["new", "strict-skill", "--out", str(tmp_path)])

        result = runner.invoke(app, ["validate", str(tmp_path / "strict-skill"), "--strict"])

        assert result.exit_code == 1
        assert "strict mode" in result.output

    def test_validate_nonexistent_dir(self, tmp_path):
        """Test that validate fails on non-existent directory."""
        result = runner.invoke(app, ["validate", str(tmp_path / "nonexistent")])

        assert result.exit_code == 1
        assert "does not exist" in result.output


class TestBundleCommand:
    """Tests for the bundle command."""

    def test_bundle_creates_zip(self, tmp_path):
        """Test that bundle creates a zip file."""
        runner.invoke(app, [
            "new", "bundle-skill", "--out", str(tmp_path),
            "-d", "A skill for bundling. Use when testing."
        ])

        output_zip = tmp_path / "output.zip"
        result = runner.invoke(app, [
            "bundle", str(tmp_path / "bundle-skill"),
            "-o", str(output_zip)
        ])

        assert result.exit_code == 0
        assert output_zip.exists()
        assert "Bundle created" in result.output

    def test_bundle_shows_stats(self, tmp_path):
        """Test that bundle shows file count and size."""
        runner.invoke(app, [
            "new", "stats-skill", "--out", str(tmp_path),
            "-d", "Test skill. Use when needed."
        ])

        result = runner.invoke(app, ["bundle", str(tmp_path / "stats-skill")])

        assert "Files:" in result.output
        assert "Size:" in result.output
        assert "bytes" in result.output

    def test_bundle_shows_upload_instructions(self, tmp_path):
        """Test that bundle shows upload instructions."""
        runner.invoke(app, [
            "new", "upload-skill", "--out", str(tmp_path),
            "-d", "Test skill. Use when needed."
        ])

        result = runner.invoke(app, ["bundle", str(tmp_path / "upload-skill")])

        assert "Upload to" in result.output
        assert "claude.ai" in result.output

    def test_bundle_fails_on_invalid_skill(self, tmp_path):
        """Test that bundle fails on invalid skill."""
        skill_dir = tmp_path / "invalid"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("Not valid frontmatter")

        result = runner.invoke(app, ["bundle", str(skill_dir)])

        assert result.exit_code == 1

    def test_bundle_no_validate(self, tmp_path):
        """Test that --no-validate skips validation."""
        runner.invoke(app, ["new", "skip-valid", "--out", str(tmp_path)])

        result = runner.invoke(app, [
            "bundle", str(tmp_path / "skip-valid"),
            "--no-validate"
        ])

        assert result.exit_code == 0


class TestShowCommand:
    """Tests for the show command."""

    def test_show_displays_skill_info(self, tmp_path):
        """Test that show displays skill information."""
        runner.invoke(app, [
            "new", "show-skill", "--out", str(tmp_path),
            "-d", "Test description here."
        ])

        result = runner.invoke(app, ["show", str(tmp_path / "show-skill")])

        assert result.exit_code == 0
        assert "show-skill" in result.output
        assert "Test description" in result.output

    def test_show_displays_files(self, tmp_path):
        """Test that show displays file listing."""
        runner.invoke(app, [
            "new", "files-skill", "--out", str(tmp_path),
            "--with-scripts"
        ])

        result = runner.invoke(app, ["show", str(tmp_path / "files-skill")])

        assert "Files" in result.output
        assert "SKILL.md" in result.output
        assert "scripts" in result.output

    def test_show_invalid_skill(self, tmp_path):
        """Test that show fails on invalid skill."""
        result = runner.invoke(app, ["show", str(tmp_path / "nonexistent")])

        assert result.exit_code == 1


class TestPreviewCommand:
    """Tests for the preview command."""

    def test_preview_shows_content(self, tmp_path):
        """Test that preview shows skill content."""
        runner.invoke(app, [
            "new", "preview-skill", "--out", str(tmp_path),
            "-d", "Preview test description."
        ])

        result = runner.invoke(app, ["preview", str(tmp_path / "preview-skill")])

        assert result.exit_code == 0
        assert "System Prompt Entry" in result.output
        assert "SKILL.md Content" in result.output

    def test_preview_shows_description(self, tmp_path):
        """Test that preview shows how description appears."""
        runner.invoke(app, [
            "new", "desc-skill", "--out", str(tmp_path),
            "-d", "This is the visible description."
        ])

        result = runner.invoke(app, ["preview", str(tmp_path / "desc-skill")])

        assert "This is the visible description" in result.output


class TestDoctorCommand:
    """Tests for the doctor command."""

    def test_doctor_runs_checks(self):
        """Test that doctor runs and displays check results."""
        result = runner.invoke(app, ["doctor"])

        assert "Environment Check" in result.output
        assert "Python" in result.output

    def test_doctor_checks_packages(self):
        """Test that doctor checks required packages."""
        result = runner.invoke(app, ["doctor"])

        assert "typer" in result.output
        assert "rich" in result.output
        assert "pyyaml" in result.output


class TestInitCommand:
    """Tests for the init command."""

    def test_init_creates_skills_dir(self, tmp_path):
        """Test that init creates skills directory."""
        result = runner.invoke(app, ["init", str(tmp_path)])

        assert result.exit_code == 0
        assert (tmp_path / "skills").exists()
        assert "Created skills directory" in result.output

    def test_init_creates_sample_skill(self, tmp_path):
        """Test that init creates sample skill."""
        result = runner.invoke(app, ["init", str(tmp_path)])

        assert (tmp_path / "skills" / "example-skill").exists()
        assert (tmp_path / "skills" / "example-skill" / "SKILL.md").exists()

    def test_init_shows_getting_started(self, tmp_path):
        """Test that init shows getting started info."""
        result = runner.invoke(app, ["init", str(tmp_path)])

        assert "Getting started" in result.output


class TestListCommand:
    """Tests for the list command."""

    def test_list_shows_skills(self, tmp_path):
        """Test that list shows skills in directory."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        runner.invoke(app, [
            "new", "skill-one", "--out", str(skills_dir),
            "-d", "First skill."
        ])
        runner.invoke(app, [
            "new", "skill-two", "--out", str(skills_dir),
            "-d", "Second skill."
        ])

        result = runner.invoke(app, ["list", str(skills_dir)])

        assert "skill-one" in result.output
        assert "skill-two" in result.output
        assert "Found 2 skill" in result.output

    def test_list_empty_directory(self, tmp_path):
        """Test list with no skills."""
        result = runner.invoke(app, ["list", str(tmp_path)])

        assert "No skills found" in result.output

    def test_list_nonexistent_directory(self, tmp_path):
        """Test list with non-existent directory."""
        result = runner.invoke(app, ["list", str(tmp_path / "nonexistent")])

        assert "not found" in result.output


class TestAddCommand:
    """Tests for the add command."""

    def test_add_doc(self, tmp_path):
        """Test adding a reference document."""
        runner.invoke(app, ["new", "add-doc-skill", "--out", str(tmp_path)])

        result = runner.invoke(app, [
            "add", str(tmp_path / "add-doc-skill"), "doc", "REFERENCE"
        ])

        assert result.exit_code == 0
        assert "Created document" in result.output
        assert (tmp_path / "add-doc-skill" / "REFERENCE.md").exists()

    def test_add_script(self, tmp_path):
        """Test adding a script."""
        runner.invoke(app, ["new", "add-script-skill", "--out", str(tmp_path)])

        result = runner.invoke(app, [
            "add", str(tmp_path / "add-script-skill"), "script", "helper"
        ])

        assert result.exit_code == 0
        assert "Created script" in result.output
        assert (tmp_path / "add-script-skill" / "scripts" / "helper.py").exists()

    def test_add_bash_script(self, tmp_path):
        """Test adding a bash script."""
        runner.invoke(app, ["new", "bash-skill", "--out", str(tmp_path)])

        result = runner.invoke(app, [
            "add", str(tmp_path / "bash-skill"), "script", "build",
            "--language", "bash"
        ])

        assert result.exit_code == 0
        assert (tmp_path / "bash-skill" / "scripts" / "build.sh").exists()

    def test_add_unknown_type(self, tmp_path):
        """Test adding unknown item type fails."""
        runner.invoke(app, ["new", "unknown-skill", "--out", str(tmp_path)])

        result = runner.invoke(app, [
            "add", str(tmp_path / "unknown-skill"), "unknown", "item"
        ])

        assert result.exit_code == 1
        assert "Unknown item type" in result.output
