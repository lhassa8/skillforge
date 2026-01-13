"""Tests for check execution."""

import pytest

from skillforge.checks import (
    execute_check,
    CheckResult,
)
from skillforge.executor import StepResult


class TestFileExistsCheck:
    """Tests for file_exists check."""

    def test_file_exists(self, tmp_path):
        """Test check passes when file exists."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        check = {
            "id": "test_check",
            "type": "file_exists",
            "path": str(test_file),
        }

        result = execute_check(check, {}, {})

        assert result.status == "passed"

    def test_file_not_exists(self, tmp_path):
        """Test check fails when file doesn't exist."""
        check = {
            "id": "test_check",
            "type": "file_exists",
            "path": str(tmp_path / "nonexistent.txt"),
        }

        result = execute_check(check, {}, {})

        assert result.status == "failed"


class TestFileContainsCheck:
    """Tests for file_contains check."""

    def test_contains_string(self, tmp_path):
        """Test check passes when file contains string."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello World!")

        check = {
            "id": "test_check",
            "type": "file_contains",
            "path": str(test_file),
            "contains": "World",
        }

        result = execute_check(check, {}, {})

        assert result.status == "passed"

    def test_not_contains_string(self, tmp_path):
        """Test check fails when file doesn't contain string."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello World!")

        check = {
            "id": "test_check",
            "type": "file_contains",
            "path": str(test_file),
            "contains": "Goodbye",
        }

        result = execute_check(check, {}, {})

        assert result.status == "failed"

    def test_matches_regex(self, tmp_path):
        """Test check passes when file matches regex."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("version = 1.2.3")

        check = {
            "id": "test_check",
            "type": "file_contains",
            "path": str(test_file),
            "regex": r"version = \d+\.\d+\.\d+",
        }

        result = execute_check(check, {}, {})

        assert result.status == "passed"


class TestExitCodeCheck:
    """Tests for exit_code check."""

    def test_exit_code_matches(self):
        """Test check passes when exit code matches."""
        step_results = {
            "step1": StepResult(
                step_id="step1",
                step_type="shell",
                status="success",
                exit_code=0,
            ),
        }

        check = {
            "id": "test_check",
            "type": "exit_code",
            "step_id": "step1",
            "equals": 0,
        }

        result = execute_check(check, {}, step_results)

        assert result.status == "passed"

    def test_exit_code_mismatch(self):
        """Test check fails when exit code doesn't match."""
        step_results = {
            "step1": StepResult(
                step_id="step1",
                step_type="shell",
                status="failed",
                exit_code=1,
            ),
        }

        check = {
            "id": "test_check",
            "type": "exit_code",
            "step_id": "step1",
            "equals": 0,
        }

        result = execute_check(check, {}, step_results)

        assert result.status == "failed"

    def test_step_not_found(self):
        """Test check fails when step doesn't exist."""
        check = {
            "id": "test_check",
            "type": "exit_code",
            "step_id": "nonexistent",
            "equals": 0,
        }

        result = execute_check(check, {}, {})

        assert result.status == "failed"
        assert "not found" in result.message.lower()


class TestStdoutContainsCheck:
    """Tests for stdout_contains check."""

    def test_stdout_contains(self):
        """Test check passes when stdout contains string."""
        step_results = {
            "step1": StepResult(
                step_id="step1",
                step_type="shell",
                status="success",
                stdout="Hello World!",
            ),
        }

        check = {
            "id": "test_check",
            "type": "stdout_contains",
            "step_id": "step1",
            "contains": "World",
        }

        result = execute_check(check, {}, step_results)

        assert result.status == "passed"

    def test_stdout_not_contains(self):
        """Test check fails when stdout doesn't contain string."""
        step_results = {
            "step1": StepResult(
                step_id="step1",
                step_type="shell",
                status="success",
                stdout="Hello World!",
            ),
        }

        check = {
            "id": "test_check",
            "type": "stdout_contains",
            "step_id": "step1",
            "contains": "Goodbye",
        }

        result = execute_check(check, {}, step_results)

        assert result.status == "failed"


class TestUnknownCheckType:
    """Tests for unknown check types."""

    def test_unknown_type_fails(self):
        """Test that unknown check type fails."""
        check = {
            "id": "test_check",
            "type": "unknown_type",
        }

        result = execute_check(check, {}, {})

        assert result.status == "failed"
        assert "Unknown check type" in result.message
