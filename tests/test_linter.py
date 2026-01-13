"""Tests for the linter module."""

import pytest
import yaml

from skillforge.linter import (
    lint_skill,
    LintSeverity,
    LintIssue,
    LintResult,
)


def create_skill(tmp_path, skill_data: dict, name: str = "test_skill"):
    """Helper to create a skill directory with given data."""
    skill_dir = tmp_path / name
    skill_dir.mkdir()
    (skill_dir / "skill.yaml").write_text(yaml.dump(skill_data))
    (skill_dir / "fixtures").mkdir()
    (skill_dir / "fixtures" / "happy_path").mkdir()
    return skill_dir


class TestLintResult:
    """Tests for LintResult class."""

    def test_has_errors_with_load_error(self):
        """Test has_errors returns True when there's a load error."""
        result = LintResult(skill_dir=None, load_error="Test error")
        assert result.has_errors is True

    def test_has_errors_with_error_issues(self):
        """Test has_errors returns True when there are error issues."""
        result = LintResult(
            skill_dir=None,
            issues=[LintIssue(LintSeverity.ERROR, "E001", "Test")],
        )
        assert result.has_errors is True

    def test_has_errors_false_for_warnings_only(self):
        """Test has_errors returns False when only warnings."""
        result = LintResult(
            skill_dir=None,
            issues=[LintIssue(LintSeverity.WARNING, "W001", "Test")],
        )
        assert result.has_errors is False

    def test_error_count(self):
        """Test error_count property."""
        result = LintResult(
            skill_dir=None,
            issues=[
                LintIssue(LintSeverity.ERROR, "E001", "Test"),
                LintIssue(LintSeverity.WARNING, "W001", "Test"),
                LintIssue(LintSeverity.ERROR, "E002", "Test"),
            ],
        )
        assert result.error_count == 2


class TestRequiredFields:
    """Tests for required field validation."""

    def test_error_if_name_missing(self, tmp_path):
        """Test that missing name field is an error."""
        skill_dir = create_skill(tmp_path, {"steps": [], "inputs": []})
        result = lint_skill(skill_dir)

        assert result.has_errors
        error_codes = [i.code for i in result.issues if i.severity == LintSeverity.ERROR]
        assert "E001" in error_codes

    def test_error_if_steps_missing(self, tmp_path):
        """Test that missing steps field is an error."""
        skill_dir = create_skill(tmp_path, {"name": "test", "inputs": []})
        result = lint_skill(skill_dir)

        assert result.has_errors
        error_codes = [i.code for i in result.issues if i.severity == LintSeverity.ERROR]
        assert "E002" in error_codes

    def test_error_if_inputs_missing(self, tmp_path):
        """Test that missing inputs field is an error."""
        skill_dir = create_skill(tmp_path, {"name": "test", "steps": []})
        result = lint_skill(skill_dir)

        assert result.has_errors
        error_codes = [i.code for i in result.issues if i.severity == LintSeverity.ERROR]
        assert "E003" in error_codes


class TestStepValidation:
    """Tests for step validation."""

    def test_error_if_steps_empty(self, tmp_path):
        """Test that empty steps list is an error."""
        skill_dir = create_skill(tmp_path, {
            "name": "test",
            "inputs": [],
            "steps": [],
        })
        result = lint_skill(skill_dir)

        error_codes = [i.code for i in result.issues if i.severity == LintSeverity.ERROR]
        assert "E004" in error_codes

    def test_error_for_duplicate_step_ids(self, tmp_path):
        """Test that duplicate step IDs are an error."""
        skill_dir = create_skill(tmp_path, {
            "name": "test",
            "inputs": [],
            "steps": [
                {"id": "step1", "type": "shell", "command": "echo 1"},
                {"id": "step1", "type": "shell", "command": "echo 2"},
            ],
        })
        result = lint_skill(skill_dir)

        error_codes = [i.code for i in result.issues if i.severity == LintSeverity.ERROR]
        assert "E008" in error_codes

    def test_error_for_missing_step_id(self, tmp_path):
        """Test that missing step ID is an error."""
        skill_dir = create_skill(tmp_path, {
            "name": "test",
            "inputs": [],
            "steps": [
                {"type": "shell", "command": "echo test"},
            ],
        })
        result = lint_skill(skill_dir)

        error_codes = [i.code for i in result.issues if i.severity == LintSeverity.ERROR]
        assert "E007" in error_codes


class TestCheckValidation:
    """Tests for check validation."""

    def test_warning_if_no_checks(self, tmp_path):
        """Test that missing checks produces a warning."""
        skill_dir = create_skill(tmp_path, {
            "name": "test",
            "inputs": [],
            "steps": [{"id": "step1", "type": "shell", "command": "echo test"}],
        })
        result = lint_skill(skill_dir)

        warning_codes = [i.code for i in result.issues if i.severity == LintSeverity.WARNING]
        assert "W001" in warning_codes

    def test_error_for_invalid_step_reference(self, tmp_path):
        """Test that referencing non-existent step is an error."""
        skill_dir = create_skill(tmp_path, {
            "name": "test",
            "inputs": [],
            "steps": [{"id": "step1", "type": "shell", "command": "echo test"}],
            "checks": [{"id": "check1", "type": "exit_code", "step_id": "nonexistent", "equals": 0}],
        })
        result = lint_skill(skill_dir)

        error_codes = [i.code for i in result.issues if i.severity == LintSeverity.ERROR]
        assert "E010" in error_codes

    def test_warning_for_unreferenced_step(self, tmp_path):
        """Test that steps without checks produce a warning."""
        skill_dir = create_skill(tmp_path, {
            "name": "test",
            "inputs": [],
            "steps": [
                {"id": "step1", "type": "shell", "command": "echo test"},
                {"id": "step2", "type": "shell", "command": "echo test2"},
            ],
            "checks": [{"id": "check1", "type": "exit_code", "step_id": "step1", "equals": 0}],
        })
        result = lint_skill(skill_dir)

        warning_codes = [i.code for i in result.issues if i.severity == LintSeverity.WARNING]
        assert "W002" in warning_codes


class TestPlaceholderValidation:
    """Tests for placeholder validation."""

    def test_error_for_unknown_placeholder(self, tmp_path):
        """Test that unknown placeholders are an error."""
        skill_dir = create_skill(tmp_path, {
            "name": "test",
            "inputs": [{"name": "target_dir", "type": "path"}],
            "steps": [{"id": "step1", "type": "shell", "command": "echo {unknown_var}"}],
        })
        result = lint_skill(skill_dir)

        error_codes = [i.code for i in result.issues if i.severity == LintSeverity.ERROR]
        assert "E013" in error_codes

    def test_valid_builtin_placeholders(self, tmp_path):
        """Test that built-in placeholders are valid."""
        skill_dir = create_skill(tmp_path, {
            "name": "test",
            "inputs": [{"name": "target_dir", "type": "path"}],
            "steps": [{"id": "step1", "type": "shell", "command": "cd {target_dir} && ls {sandbox_dir}"}],
            "checks": [{"id": "check1", "type": "exit_code", "step_id": "step1", "equals": 0}],
        })
        result = lint_skill(skill_dir)

        # Should not have E013 errors for built-in placeholders
        error_codes = [i.code for i in result.issues if i.severity == LintSeverity.ERROR]
        assert "E013" not in error_codes

    def test_valid_input_placeholders(self, tmp_path):
        """Test that input-defined placeholders are valid."""
        skill_dir = create_skill(tmp_path, {
            "name": "test",
            "inputs": [
                {"name": "target_dir", "type": "path"},
                {"name": "version", "type": "string"},
            ],
            "steps": [{"id": "step1", "type": "shell", "command": "echo {version}"}],
            "checks": [{"id": "check1", "type": "exit_code", "step_id": "step1", "equals": 0}],
        })
        result = lint_skill(skill_dir)

        error_codes = [i.code for i in result.issues if i.severity == LintSeverity.ERROR]
        assert "E013" not in error_codes


class TestAbsolutePathValidation:
    """Tests for absolute path validation."""

    def test_error_for_absolute_path(self, tmp_path):
        """Test that absolute paths are an error."""
        skill_dir = create_skill(tmp_path, {
            "name": "test",
            "inputs": [],
            "steps": [{"id": "step1", "type": "shell", "command": "echo test", "cwd": "/absolute/path"}],
        })
        result = lint_skill(skill_dir)

        error_codes = [i.code for i in result.issues if i.severity == LintSeverity.ERROR]
        assert "E014" in error_codes

    def test_placeholder_paths_are_valid(self, tmp_path):
        """Test that placeholder-prefixed paths are valid."""
        skill_dir = create_skill(tmp_path, {
            "name": "test",
            "inputs": [{"name": "target_dir", "type": "path"}],
            "steps": [{"id": "step1", "type": "shell", "command": "echo test", "cwd": "{target_dir}"}],
            "checks": [{"id": "check1", "type": "exit_code", "step_id": "step1", "equals": 0}],
        })
        result = lint_skill(skill_dir)

        error_codes = [i.code for i in result.issues if i.severity == LintSeverity.ERROR]
        assert "E014" not in error_codes


class TestShellCommandValidation:
    """Tests for shell command validation."""

    def test_warning_for_nondeterministic_date(self, tmp_path):
        """Test that 'date' command produces a warning."""
        skill_dir = create_skill(tmp_path, {
            "name": "test",
            "inputs": [{"name": "target_dir", "type": "path"}],
            "steps": [{"id": "step1", "type": "shell", "command": "date > timestamp.txt"}],
            "checks": [{"id": "check1", "type": "exit_code", "step_id": "step1", "equals": 0}],
        })
        result = lint_skill(skill_dir)

        warning_codes = [i.code for i in result.issues if i.severity == LintSeverity.WARNING]
        assert "W003" in warning_codes

    def test_warning_for_sudo(self, tmp_path):
        """Test that 'sudo' command produces a warning."""
        skill_dir = create_skill(tmp_path, {
            "name": "test",
            "inputs": [{"name": "target_dir", "type": "path"}],
            "steps": [{"id": "step1", "type": "shell", "command": "sudo rm file.txt"}],
            "checks": [{"id": "check1", "type": "exit_code", "step_id": "step1", "equals": 0}],
        })
        result = lint_skill(skill_dir)

        warning_codes = [i.code for i in result.issues if i.severity == LintSeverity.WARNING]
        assert "W004" in warning_codes

    def test_warning_for_rm_rf(self, tmp_path):
        """Test that 'rm -rf' command produces a warning."""
        skill_dir = create_skill(tmp_path, {
            "name": "test",
            "inputs": [{"name": "target_dir", "type": "path"}],
            "steps": [{"id": "step1", "type": "shell", "command": "rm -rf temp/"}],
            "checks": [{"id": "check1", "type": "exit_code", "step_id": "step1", "equals": 0}],
        })
        result = lint_skill(skill_dir)

        warning_codes = [i.code for i in result.issues if i.severity == LintSeverity.WARNING]
        assert "W004" in warning_codes


class TestFileStructureValidation:
    """Tests for file structure validation."""

    def test_warning_for_missing_happy_path(self, tmp_path):
        """Test that missing happy_path fixture produces a warning."""
        skill_dir = tmp_path / "test_skill"
        skill_dir.mkdir()
        (skill_dir / "skill.yaml").write_text(yaml.dump({
            "name": "test",
            "inputs": [{"name": "target_dir", "type": "path"}],
            "steps": [{"id": "step1", "type": "shell", "command": "echo test"}],
            "checks": [{"id": "check1", "type": "exit_code", "step_id": "step1", "equals": 0}],
        }))

        result = lint_skill(skill_dir)

        warning_codes = [i.code for i in result.issues if i.severity == LintSeverity.WARNING]
        assert "W005" in warning_codes


class TestValidSkill:
    """Tests for valid skills."""

    def test_valid_skill_no_errors(self, tmp_path):
        """Test that a valid skill has no errors."""
        skill_dir = create_skill(tmp_path, {
            "name": "valid_skill",
            "version": "1.0.0",
            "description": "A valid skill",
            "inputs": [{"name": "target_dir", "type": "path"}],
            "steps": [
                {"id": "step1", "type": "shell", "command": "echo hello", "cwd": "{target_dir}"},
            ],
            "checks": [
                {"id": "check1", "type": "exit_code", "step_id": "step1", "equals": 0},
            ],
        })
        result = lint_skill(skill_dir)

        assert not result.has_errors

    def test_load_error_for_nonexistent_dir(self, tmp_path):
        """Test that nonexistent directory produces a load error."""
        result = lint_skill(tmp_path / "nonexistent")

        assert result.load_error is not None
        assert result.has_errors
