"""Tests for skill runner."""

import json
import pytest
import yaml

from skillforge.runner import (
    run_skill,
    get_run_summary,
    RunReport,
)


def create_test_skill(tmp_path, skill_data: dict, name: str = "test_skill"):
    """Helper to create a test skill directory."""
    skill_dir = tmp_path / name
    skill_dir.mkdir()
    (skill_dir / "skill.yaml").write_text(yaml.dump(skill_data))
    (skill_dir / "fixtures").mkdir()
    (skill_dir / "fixtures" / "happy_path").mkdir()
    (skill_dir / "reports").mkdir()
    return skill_dir


def create_test_target(tmp_path, name: str = "target"):
    """Helper to create a test target directory."""
    target_dir = tmp_path / name
    target_dir.mkdir()
    (target_dir / "README.md").write_text("# Test Project")
    return target_dir


class TestRunSkill:
    """Tests for run_skill function."""

    def test_successful_run(self, tmp_path):
        """Test successful skill execution."""
        skill_dir = create_test_skill(tmp_path, {
            "name": "test_skill",
            "inputs": [{"name": "target_dir", "type": "path"}],
            "steps": [
                {"id": "step1", "type": "shell", "command": "echo 'hello'"},
            ],
            "checks": [
                {"id": "check1", "type": "exit_code", "step_id": "step1", "equals": 0},
            ],
        })
        target_dir = create_test_target(tmp_path)

        report = run_skill(skill_dir, target_dir)

        assert report.success is True
        assert len(report.steps) == 1
        assert report.steps[0]["status"] == "success"
        assert len(report.checks) == 1
        assert report.checks[0]["status"] == "passed"

    def test_failed_step(self, tmp_path):
        """Test skill with failing step."""
        skill_dir = create_test_skill(tmp_path, {
            "name": "test_skill",
            "inputs": [{"name": "target_dir", "type": "path"}],
            "steps": [
                {"id": "step1", "type": "shell", "command": "exit 1"},
            ],
            "checks": [],
        })
        target_dir = create_test_target(tmp_path)

        report = run_skill(skill_dir, target_dir)

        assert report.success is False
        assert report.failed_step_id == "step1"

    def test_failed_check(self, tmp_path):
        """Test skill with failing check."""
        skill_dir = create_test_skill(tmp_path, {
            "name": "test_skill",
            "inputs": [{"name": "target_dir", "type": "path"}],
            "steps": [
                {"id": "step1", "type": "shell", "command": "echo 'hello'"},
            ],
            "checks": [
                {"id": "check1", "type": "exit_code", "step_id": "step1", "equals": 99},
            ],
        })
        target_dir = create_test_target(tmp_path)

        report = run_skill(skill_dir, target_dir)

        assert report.success is False
        assert "check" in report.error_message.lower()

    def test_dry_run(self, tmp_path):
        """Test dry run mode."""
        skill_dir = create_test_skill(tmp_path, {
            "name": "test_skill",
            "inputs": [{"name": "target_dir", "type": "path"}],
            "steps": [
                {"id": "step1", "type": "shell", "command": "echo 'should not run'"},
            ],
            "checks": [],
        })
        target_dir = create_test_target(tmp_path)

        report = run_skill(skill_dir, target_dir, dry_run=True)

        assert report.mode == "dry_run"
        assert len(report.steps) == 1
        assert report.steps[0]["status"] == "skipped"

    def test_sandbox_created(self, tmp_path):
        """Test that sandbox is created."""
        skill_dir = create_test_skill(tmp_path, {
            "name": "test_skill",
            "inputs": [{"name": "target_dir", "type": "path"}],
            "steps": [
                {"id": "step1", "type": "shell", "command": "ls"},
            ],
            "checks": [],
        })
        target_dir = create_test_target(tmp_path)

        report = run_skill(skill_dir, target_dir)

        # Sandbox should be in reports directory
        assert "sandbox" in report.sandbox_path
        assert report.sandbox_path != str(target_dir)

    def test_no_sandbox_mode(self, tmp_path):
        """Test no-sandbox mode."""
        skill_dir = create_test_skill(tmp_path, {
            "name": "test_skill",
            "inputs": [{"name": "target_dir", "type": "path"}],
            "steps": [
                {"id": "step1", "type": "shell", "command": "echo test"},
            ],
            "checks": [],
        })
        target_dir = create_test_target(tmp_path)

        report = run_skill(skill_dir, target_dir, no_sandbox=True)

        assert report.sandbox_path == str(target_dir)

    def test_writes_report(self, tmp_path):
        """Test that run report is written to disk."""
        skill_dir = create_test_skill(tmp_path, {
            "name": "test_skill",
            "inputs": [{"name": "target_dir", "type": "path"}],
            "steps": [
                {"id": "step1", "type": "shell", "command": "echo hello"},
            ],
            "checks": [],
        })
        target_dir = create_test_target(tmp_path)

        report = run_skill(skill_dir, target_dir)

        # Check report file exists
        report_dir = skill_dir / "reports" / f"run_{report.run_id}"
        assert report_dir.exists()
        assert (report_dir / "run_report.json").exists()

        # Verify JSON content
        with open(report_dir / "run_report.json") as f:
            saved_report = json.load(f)
        assert saved_report["skill_name"] == "test_skill"

    def test_placeholder_substitution(self, tmp_path):
        """Test that placeholders are substituted in steps."""
        skill_dir = create_test_skill(tmp_path, {
            "name": "test_skill",
            "inputs": [
                {"name": "target_dir", "type": "path"},
                {"name": "message", "type": "string", "default": "hello"},
            ],
            "steps": [
                {"id": "step1", "type": "shell", "command": "echo '{message}'"},
            ],
            "checks": [],
        })
        target_dir = create_test_target(tmp_path)

        report = run_skill(skill_dir, target_dir)

        assert report.success is True
        # The resolved command should contain the actual message
        assert report.steps[0]["command"] == "echo 'hello'"


class TestGetRunSummary:
    """Tests for get_run_summary function."""

    def test_summary_counts(self):
        """Test that summary counts are correct."""
        report = RunReport(
            run_id="test",
            skill_name="test_skill",
            skill_dir="/test",
            started_at="2024-01-01T00:00:00",
            finished_at="2024-01-01T00:00:01",
            steps=[
                {"id": "s1", "status": "success", "duration_ms": 100},
                {"id": "s2", "status": "success", "duration_ms": 200},
                {"id": "s3", "status": "failed", "duration_ms": 50},
            ],
            checks=[
                {"id": "c1", "status": "passed"},
                {"id": "c2", "status": "failed"},
            ],
            success=False,
        )

        summary = get_run_summary(report)

        assert summary["steps_total"] == 3
        assert summary["steps_passed"] == 2
        assert summary["steps_failed"] == 1
        assert summary["checks_total"] == 2
        assert summary["checks_passed"] == 1
        assert summary["checks_failed"] == 1
        assert summary["duration_ms"] == 350


class TestSkillNotFound:
    """Tests for error handling."""

    def test_skill_not_found(self, tmp_path):
        """Test error when skill directory doesn't exist."""
        target_dir = create_test_target(tmp_path)

        report = run_skill(tmp_path / "nonexistent", target_dir)

        assert report.success is False
        assert "load" in report.error_message.lower()

    def test_target_not_found(self, tmp_path):
        """Test error when target directory doesn't exist."""
        skill_dir = create_test_skill(tmp_path, {
            "name": "test_skill",
            "inputs": [],
            "steps": [],
            "checks": [],
        })

        report = run_skill(skill_dir, tmp_path / "nonexistent")

        assert report.success is False
        assert "sandbox" in report.error_message.lower() or "target" in report.error_message.lower()
