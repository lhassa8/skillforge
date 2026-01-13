"""Tests for the doctor module."""

from unittest.mock import patch, MagicMock
import subprocess
import sys

import pytest

from skillforge.doctor import (
    CheckStatus,
    CheckResult,
    check_python_version,
    check_git,
    check_rsync,
    check_config_initialized,
    run_all_checks,
    has_errors,
    has_warnings,
)


class TestCheckPythonVersion:
    """Tests for Python version checking."""

    def test_returns_ok_for_valid_version(self):
        """Test that current Python version passes (we're running on 3.11+)."""
        result = check_python_version()
        # We're running tests on Python 3.11+, so this should pass
        assert result.status == CheckStatus.OK
        assert result.name == "Python"
        assert result.version is not None

    def test_returns_error_for_old_version(self):
        """Test that old Python versions fail."""
        # Create a mock version_info using MagicMock
        mock_version = MagicMock()
        mock_version.major = 3
        mock_version.minor = 10
        mock_version.micro = 0
        with patch.object(sys, "version_info", mock_version):
            result = check_python_version()
            assert result.status == CheckStatus.ERROR
            assert "3.11+" in result.message


class TestCheckGit:
    """Tests for git availability checking."""

    def test_returns_ok_when_git_available(self):
        """Test that git check passes when git is available."""
        result = check_git()
        # Assuming git is installed on the test system
        assert result.status == CheckStatus.OK
        assert result.name == "Git"

    def test_returns_error_when_git_not_found(self):
        """Test that git check fails when git is not in PATH."""
        with patch("shutil.which", return_value=None):
            result = check_git()
            assert result.status == CheckStatus.ERROR
            assert "not found" in result.message

    def test_returns_error_when_git_fails(self):
        """Test that git check fails when git command fails."""
        with patch("shutil.which", return_value="/usr/bin/git"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=1)
                result = check_git()
                assert result.status == CheckStatus.ERROR

    def test_handles_timeout(self):
        """Test that git check handles timeout gracefully."""
        with patch("shutil.which", return_value="/usr/bin/git"):
            with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("git", 10)):
                result = check_git()
                assert result.status == CheckStatus.ERROR
                assert "timed out" in result.message


class TestCheckRsync:
    """Tests for rsync availability checking."""

    def test_returns_warning_when_rsync_not_found(self):
        """Test that rsync check returns warning when not found."""
        with patch("shutil.which", return_value=None):
            result = check_rsync()
            assert result.status == CheckStatus.WARNING
            assert "shutil.copytree" in result.message

    def test_returns_ok_when_rsync_available(self):
        """Test that rsync check passes when rsync is available."""
        with patch("shutil.which", return_value="/usr/bin/rsync"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0,
                    stdout="rsync  version 3.2.7  protocol version 31\n"
                )
                result = check_rsync()
                assert result.status == CheckStatus.OK


class TestCheckConfigInitialized:
    """Tests for config initialization checking."""

    def test_returns_warning_when_config_dir_missing(self, tmp_path):
        """Test that config check returns warning when dir doesn't exist."""
        from skillforge import config

        fake_dir = tmp_path / "nonexistent"
        with patch.object(config, "CONFIG_DIR", fake_dir):
            result = check_config_initialized()
            assert result.status == CheckStatus.WARNING
            assert "skillforge init" in result.message

    def test_returns_ok_when_config_exists(self, tmp_path):
        """Test that config check passes when config exists."""
        from skillforge import config

        config_dir = tmp_path / ".skillforge"
        config_dir.mkdir()
        config_file = config_dir / "config.yaml"
        config_file.write_text("default_shell: bash\n")

        with patch.object(config, "CONFIG_DIR", config_dir):
            with patch.object(config, "CONFIG_FILE", config_file):
                result = check_config_initialized()
                assert result.status == CheckStatus.OK


class TestRunAllChecks:
    """Tests for running all checks."""

    def test_returns_list_of_results(self):
        """Test that run_all_checks returns a list of CheckResult objects."""
        results = run_all_checks()
        assert isinstance(results, list)
        assert len(results) > 0
        assert all(isinstance(r, CheckResult) for r in results)

    def test_includes_all_check_types(self):
        """Test that all expected checks are included."""
        results = run_all_checks()
        check_names = [r.name for r in results]
        assert "Python" in check_names
        assert "Git" in check_names
        assert "rsync" in check_names
        assert "Config" in check_names


class TestHasErrors:
    """Tests for error detection."""

    def test_returns_true_when_errors_present(self):
        """Test that has_errors returns True when there are errors."""
        results = [
            CheckResult("Test1", CheckStatus.OK, "OK"),
            CheckResult("Test2", CheckStatus.ERROR, "Failed"),
        ]
        assert has_errors(results) is True

    def test_returns_false_when_no_errors(self):
        """Test that has_errors returns False when there are no errors."""
        results = [
            CheckResult("Test1", CheckStatus.OK, "OK"),
            CheckResult("Test2", CheckStatus.WARNING, "Warning"),
        ]
        assert has_errors(results) is False


class TestHasWarnings:
    """Tests for warning detection."""

    def test_returns_true_when_warnings_present(self):
        """Test that has_warnings returns True when there are warnings."""
        results = [
            CheckResult("Test1", CheckStatus.OK, "OK"),
            CheckResult("Test2", CheckStatus.WARNING, "Warning"),
        ]
        assert has_warnings(results) is True

    def test_returns_false_when_no_warnings(self):
        """Test that has_warnings returns False when there are no warnings."""
        results = [
            CheckResult("Test1", CheckStatus.OK, "OK"),
            CheckResult("Test2", CheckStatus.OK, "OK"),
        ]
        assert has_warnings(results) is False
