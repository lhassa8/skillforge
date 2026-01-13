"""Tests for step execution."""

import pytest

from skillforge.executor import (
    execute_step,
    StepResult,
)


class TestShellStep:
    """Tests for shell step execution."""

    def test_successful_command(self, tmp_path):
        """Test successful shell command execution."""
        step = {
            "id": "test_step",
            "type": "shell",
            "command": "echo 'hello world'",
        }
        logs_dir = tmp_path / "logs"

        result = execute_step(step, {}, logs_dir)

        assert result.status == "success"
        assert result.exit_code == 0
        assert "hello world" in result.stdout

    def test_failed_command(self, tmp_path):
        """Test failed shell command."""
        step = {
            "id": "test_step",
            "type": "shell",
            "command": "exit 1",
        }
        logs_dir = tmp_path / "logs"

        result = execute_step(step, {}, logs_dir)

        assert result.status == "failed"
        assert result.exit_code == 1

    def test_expected_exit_code(self, tmp_path):
        """Test command with expected non-zero exit code."""
        step = {
            "id": "test_step",
            "type": "shell",
            "command": "exit 42",
            "expect_exit": 42,
        }
        logs_dir = tmp_path / "logs"

        result = execute_step(step, {}, logs_dir)

        assert result.status == "success"
        assert result.exit_code == 42

    def test_allow_failure(self, tmp_path):
        """Test command with allow_failure=True."""
        step = {
            "id": "test_step",
            "type": "shell",
            "command": "exit 1",
            "allow_failure": True,
        }
        logs_dir = tmp_path / "logs"

        result = execute_step(step, {}, logs_dir)

        assert result.status == "success"  # Allowed to fail

    def test_with_cwd(self, tmp_path):
        """Test command with working directory."""
        step = {
            "id": "test_step",
            "type": "shell",
            "command": "pwd",
            "cwd": str(tmp_path),
        }
        logs_dir = tmp_path / "logs"

        result = execute_step(step, {}, logs_dir)

        assert result.status == "success"
        assert str(tmp_path) in result.stdout

    def test_dry_run(self, tmp_path):
        """Test dry run mode."""
        step = {
            "id": "test_step",
            "type": "shell",
            "command": "echo should not run",
        }
        logs_dir = tmp_path / "logs"

        result = execute_step(step, {}, logs_dir, dry_run=True)

        assert result.status == "skipped"
        assert result.stdout == ""

    def test_placeholder_substitution(self, tmp_path):
        """Test placeholder substitution in command."""
        step = {
            "id": "test_step",
            "type": "shell",
            "command": "echo {message}",
        }
        context = {"message": "hello from placeholder"}
        logs_dir = tmp_path / "logs"

        result = execute_step(step, context, logs_dir)

        assert result.status == "success"
        assert "hello from placeholder" in result.stdout

    def test_writes_log_files(self, tmp_path):
        """Test that log files are written."""
        step = {
            "id": "test_step",
            "type": "shell",
            "command": "echo stdout_content && echo stderr_content >&2",
        }
        logs_dir = tmp_path / "logs"

        execute_step(step, {}, logs_dir)

        assert (logs_dir / "step_test_step.stdout").exists()
        assert (logs_dir / "step_test_step.stderr").exists()


class TestFileReplaceStep:
    """Tests for file.replace step execution."""

    def test_replace_content(self, tmp_path):
        """Test file content replacement."""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("version = 1.0.0")

        step = {
            "id": "test_step",
            "type": "file.replace",
            "path": str(test_file),
            "pattern": r"version = [\d.]+",
            "replace_with": "version = 2.0.0",
        }
        logs_dir = tmp_path / "logs"

        result = execute_step(step, {}, logs_dir)

        assert result.status == "success"
        assert test_file.read_text() == "version = 2.0.0"

    def test_file_not_found(self, tmp_path):
        """Test replacement on non-existent file."""
        step = {
            "id": "test_step",
            "type": "file.replace",
            "path": str(tmp_path / "nonexistent.txt"),
            "pattern": "old",
            "replace_with": "new",
        }
        logs_dir = tmp_path / "logs"

        result = execute_step(step, {}, logs_dir)

        assert result.status == "failed"
        assert "not found" in result.error_message.lower()


class TestFileTemplateStep:
    """Tests for file.template step execution."""

    def test_write_template(self, tmp_path):
        """Test writing template to file."""
        output_file = tmp_path / "output.txt"

        step = {
            "id": "test_step",
            "type": "file.template",
            "path": str(output_file),
            "template": "Name: {name}\nVersion: {version}",
        }
        context = {"name": "test", "version": "1.0.0"}
        logs_dir = tmp_path / "logs"

        result = execute_step(step, context, logs_dir)

        assert result.status == "success"
        assert output_file.exists()
        content = output_file.read_text()
        assert "Name: test" in content
        assert "Version: 1.0.0" in content

    def test_if_missing_mode_skips(self, tmp_path):
        """Test if_missing mode skips existing files."""
        output_file = tmp_path / "output.txt"
        output_file.write_text("existing content")

        step = {
            "id": "test_step",
            "type": "file.template",
            "path": str(output_file),
            "template": "new content",
            "mode": "if_missing",
        }
        logs_dir = tmp_path / "logs"

        result = execute_step(step, {}, logs_dir)

        assert result.status == "success"
        assert output_file.read_text() == "existing content"


class TestJsonPatchStep:
    """Tests for json.patch step execution."""

    def test_add_operation(self, tmp_path):
        """Test JSON add operation."""
        import json

        test_file = tmp_path / "test.json"
        test_file.write_text(json.dumps({"name": "test"}))

        step = {
            "id": "test_step",
            "type": "json.patch",
            "path": str(test_file),
            "operations": [
                {"op": "add", "path": "/version", "value": "1.0.0"},
            ],
        }
        logs_dir = tmp_path / "logs"

        result = execute_step(step, {}, logs_dir)

        assert result.status == "success"
        data = json.loads(test_file.read_text())
        assert data["version"] == "1.0.0"

    def test_merge_operation(self, tmp_path):
        """Test JSON merge operation."""
        import json

        test_file = tmp_path / "test.json"
        test_file.write_text(json.dumps({"name": "test"}))

        step = {
            "id": "test_step",
            "type": "json.patch",
            "path": str(test_file),
            "operations": [
                {"merge": {"version": "1.0.0", "author": "user"}},
            ],
        }
        logs_dir = tmp_path / "logs"

        result = execute_step(step, {}, logs_dir)

        assert result.status == "success"
        data = json.loads(test_file.read_text())
        assert data["version"] == "1.0.0"
        assert data["author"] == "user"


class TestUnknownStepType:
    """Tests for unknown step types."""

    def test_unknown_type_fails(self, tmp_path):
        """Test that unknown step type fails."""
        step = {
            "id": "test_step",
            "type": "unknown_type",
        }
        logs_dir = tmp_path / "logs"

        result = execute_step(step, {}, logs_dir)

        assert result.status == "failed"
        assert "Unknown step type" in result.error_message
