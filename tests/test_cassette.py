"""Tests for cassette recording and replay."""

import json
import pytest
import yaml

from skillforge.cassette import (
    Cassette,
    RecordedCommand,
    CassetteRecordResult,
    record_cassette,
    load_cassette,
    save_cassette,
    get_cassette_path,
    get_cassette_info,
    list_cassettes,
    replay_step_from_cassette,
)
from skillforge.executor import StepResult


def create_test_skill(tmp_path, skill_data: dict, name: str = "test_skill"):
    """Helper to create a test skill directory."""
    skill_dir = tmp_path / name
    skill_dir.mkdir()
    (skill_dir / "skill.yaml").write_text(yaml.dump(skill_data))
    (skill_dir / "fixtures").mkdir()
    (skill_dir / "cassettes").mkdir()
    (skill_dir / "reports").mkdir()
    return skill_dir


def create_fixture(skill_dir, fixture_name: str, input_files: dict = None):
    """Helper to create a fixture directory."""
    fixture_dir = skill_dir / "fixtures" / fixture_name
    fixture_dir.mkdir(parents=True)

    input_dir = fixture_dir / "input"
    input_dir.mkdir()

    if input_files:
        for filename, content in input_files.items():
            file_path = input_dir / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)

    return fixture_dir


class TestCassette:
    """Tests for Cassette dataclass."""

    def test_create_cassette(self):
        """Test creating a cassette."""
        cassette = Cassette(
            fixture_name="happy_path",
            skill_name="my_skill",
            recorded_at="2024-01-01T00:00:00",
        )

        assert cassette.fixture_name == "happy_path"
        assert cassette.skill_name == "my_skill"
        assert cassette.commands == []

    def test_add_command(self):
        """Test adding commands to a cassette."""
        cassette = Cassette(fixture_name="test")
        cassette.commands.append(
            RecordedCommand(
                step_id="step1",
                command="echo hello",
                exit_code=0,
                stdout="hello\n",
            )
        )

        assert len(cassette.commands) == 1
        assert cassette.commands[0].step_id == "step1"

    def test_find_command(self):
        """Test finding a command in a cassette."""
        cassette = Cassette(fixture_name="test")
        cassette.commands.append(
            RecordedCommand(
                step_id="step1",
                command="echo hello",
                exit_code=0,
                stdout="hello\n",
            )
        )

        found = cassette.find_command("step1", "echo hello")

        assert found is not None
        assert found.stdout == "hello\n"

    def test_find_command_not_found(self):
        """Test finding a non-existent command."""
        cassette = Cassette(fixture_name="test")
        cassette.commands.append(
            RecordedCommand(step_id="step1", command="echo hello")
        )

        found = cassette.find_command("step2", "echo hello")

        assert found is None

    def test_find_command_with_cwd(self):
        """Test finding command with cwd matching."""
        cassette = Cassette(fixture_name="test")
        cassette.commands.append(
            RecordedCommand(
                step_id="step1",
                command="ls",
                cwd="/home/user",
            )
        )

        # Should match with correct cwd
        found = cassette.find_command("step1", "ls", "/home/user")
        assert found is not None

        # Should not match with wrong cwd
        found = cassette.find_command("step1", "ls", "/other/path")
        assert found is None

    def test_to_dict(self):
        """Test converting cassette to dict."""
        cassette = Cassette(
            fixture_name="test",
            skill_name="my_skill",
            recorded_at="2024-01-01T00:00:00",
        )
        cassette.commands.append(
            RecordedCommand(
                step_id="step1",
                command="echo hello",
                exit_code=0,
                stdout="hello\n",
            )
        )

        data = cassette.to_dict()

        assert data["fixture_name"] == "test"
        assert data["skill_name"] == "my_skill"
        assert len(data["commands"]) == 1
        assert data["commands"][0]["step_id"] == "step1"

    def test_from_dict(self):
        """Test creating cassette from dict."""
        data = {
            "fixture_name": "test",
            "skill_name": "my_skill",
            "recorded_at": "2024-01-01T00:00:00",
            "commands": [
                {
                    "step_id": "step1",
                    "command": "echo hello",
                    "exit_code": 0,
                    "stdout": "hello\n",
                }
            ],
        }

        cassette = Cassette.from_dict(data)

        assert cassette.fixture_name == "test"
        assert len(cassette.commands) == 1
        assert cassette.commands[0].stdout == "hello\n"


class TestSaveLoadCassette:
    """Tests for saving and loading cassettes."""

    def test_save_cassette(self, tmp_path):
        """Test saving a cassette to disk."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()

        cassette = Cassette(
            fixture_name="happy_path",
            skill_name="test_skill",
        )
        cassette.commands.append(
            RecordedCommand(step_id="step1", command="echo test")
        )

        path = save_cassette(skill_dir, cassette)

        assert path.exists()
        assert path.name == "happy_path.yaml"

    def test_load_cassette(self, tmp_path):
        """Test loading a cassette from disk."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()

        # Save first
        cassette = Cassette(
            fixture_name="happy_path",
            skill_name="test_skill",
            recorded_at="2024-01-01T00:00:00",
        )
        cassette.commands.append(
            RecordedCommand(
                step_id="step1",
                command="echo test",
                stdout="test\n",
            )
        )
        save_cassette(skill_dir, cassette)

        # Load
        loaded = load_cassette(skill_dir, "happy_path")

        assert loaded is not None
        assert loaded.fixture_name == "happy_path"
        assert len(loaded.commands) == 1
        assert loaded.commands[0].stdout == "test\n"

    def test_load_nonexistent_cassette(self, tmp_path):
        """Test loading a cassette that doesn't exist."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()

        loaded = load_cassette(skill_dir, "nonexistent")

        assert loaded is None

    def test_get_cassette_path(self, tmp_path):
        """Test getting cassette path."""
        skill_dir = tmp_path / "skill"

        path = get_cassette_path(skill_dir, "happy_path")

        assert path == skill_dir / "cassettes" / "happy_path.yaml"


class TestRecordCassette:
    """Tests for cassette recording."""

    def test_record_successful(self, tmp_path):
        """Test successful cassette recording."""
        skill_dir = create_test_skill(tmp_path, {
            "name": "test_skill",
            "inputs": [{"name": "target_dir", "type": "path"}],
            "steps": [
                {"id": "step1", "type": "shell", "command": "echo hello"},
            ],
            "checks": [],
        })
        create_fixture(skill_dir, "happy_path", {"test.txt": "test"})

        result = record_cassette(skill_dir, "happy_path")

        assert result.success is True
        assert result.commands_recorded == 1
        assert result.cassette_path != ""

    def test_record_creates_cassette_file(self, tmp_path):
        """Test that recording creates a cassette file."""
        skill_dir = create_test_skill(tmp_path, {
            "name": "test_skill",
            "inputs": [{"name": "target_dir", "type": "path"}],
            "steps": [
                {"id": "step1", "type": "shell", "command": "echo hello"},
            ],
            "checks": [],
        })
        create_fixture(skill_dir, "happy_path", {"test.txt": "test"})

        record_cassette(skill_dir, "happy_path")

        cassette_path = skill_dir / "cassettes" / "happy_path.yaml"
        assert cassette_path.exists()

    def test_record_captures_stdout(self, tmp_path):
        """Test that recording captures stdout."""
        skill_dir = create_test_skill(tmp_path, {
            "name": "test_skill",
            "inputs": [{"name": "target_dir", "type": "path"}],
            "steps": [
                {"id": "step1", "type": "shell", "command": "echo captured_output"},
            ],
            "checks": [],
        })
        create_fixture(skill_dir, "happy_path", {"test.txt": "test"})

        record_cassette(skill_dir, "happy_path")

        cassette = load_cassette(skill_dir, "happy_path")
        assert "captured_output" in cassette.commands[0].stdout

    def test_record_fixture_not_found(self, tmp_path):
        """Test recording with non-existent fixture."""
        skill_dir = create_test_skill(tmp_path, {
            "name": "test_skill",
            "steps": [],
            "checks": [],
        })

        result = record_cassette(skill_dir, "nonexistent")

        assert result.success is False
        assert "not found" in result.error_message.lower()

    def test_record_multiple_steps(self, tmp_path):
        """Test recording multiple shell steps."""
        skill_dir = create_test_skill(tmp_path, {
            "name": "test_skill",
            "inputs": [{"name": "target_dir", "type": "path"}],
            "steps": [
                {"id": "step1", "type": "shell", "command": "echo first"},
                {"id": "step2", "type": "shell", "command": "echo second"},
                {"id": "step3", "type": "shell", "command": "echo third"},
            ],
            "checks": [],
        })
        create_fixture(skill_dir, "happy_path", {"test.txt": "test"})

        result = record_cassette(skill_dir, "happy_path")

        assert result.success is True
        assert result.commands_recorded == 3

    def test_record_only_shell_steps(self, tmp_path):
        """Test that only shell steps are recorded."""
        skill_dir = create_test_skill(tmp_path, {
            "name": "test_skill",
            "inputs": [{"name": "target_dir", "type": "path"}],
            "steps": [
                {"id": "step1", "type": "shell", "command": "echo shell"},
                {"id": "step2", "type": "file.template", "path": "{sandbox_dir}/test.txt", "template": "content"},
            ],
            "checks": [],
        })
        create_fixture(skill_dir, "happy_path", {"test.txt": "test"})

        result = record_cassette(skill_dir, "happy_path")

        # Only the shell step should be recorded
        assert result.commands_recorded == 1


class TestReplayFromCassette:
    """Tests for cassette replay."""

    def test_replay_step(self):
        """Test replaying a step from cassette."""
        cassette = Cassette(fixture_name="test")
        cassette.commands.append(
            RecordedCommand(
                step_id="step1",
                command="echo hello",
                exit_code=0,
                stdout="hello\n",
                stderr="",
                duration_ms=10,
            )
        )

        result = replay_step_from_cassette(cassette, "step1", "echo hello")

        assert result is not None
        assert result.step_id == "step1"
        assert result.status == "success"
        assert result.stdout == "hello\n"
        assert result.exit_code == 0

    def test_replay_step_not_found(self):
        """Test replay when step not in cassette."""
        cassette = Cassette(fixture_name="test")

        result = replay_step_from_cassette(cassette, "step1", "echo hello")

        assert result is None

    def test_replay_failed_step(self):
        """Test replaying a failed step."""
        cassette = Cassette(fixture_name="test")
        cassette.commands.append(
            RecordedCommand(
                step_id="step1",
                command="exit 1",
                exit_code=1,
                stderr="error\n",
            )
        )

        result = replay_step_from_cassette(cassette, "step1", "exit 1")

        assert result is not None
        assert result.status == "failed"
        assert result.exit_code == 1


class TestGetCassetteInfo:
    """Tests for get_cassette_info function."""

    def test_no_cassette(self, tmp_path):
        """Test info when no cassette exists."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()

        info = get_cassette_info(skill_dir, "nonexistent")

        assert info == {}

    def test_existing_cassette(self, tmp_path):
        """Test info for existing cassette."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()

        cassette = Cassette(
            fixture_name="happy_path",
            skill_name="test_skill",
            recorded_at="2024-01-01T00:00:00",
        )
        cassette.commands.append(
            RecordedCommand(step_id="step1", command="echo test")
        )
        save_cassette(skill_dir, cassette)

        info = get_cassette_info(skill_dir, "happy_path")

        assert info["exists"] is True
        assert info["fixture_name"] == "happy_path"
        assert info["skill_name"] == "test_skill"
        assert info["commands_count"] == 1


class TestListCassettes:
    """Tests for list_cassettes function."""

    def test_no_cassettes(self, tmp_path):
        """Test listing when no cassettes exist."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()

        cassettes = list_cassettes(skill_dir)

        assert cassettes == []

    def test_list_multiple_cassettes(self, tmp_path):
        """Test listing multiple cassettes."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()

        # Create multiple cassettes
        for name in ["fixture1", "fixture2", "fixture3"]:
            cassette = Cassette(
                fixture_name=name,
                skill_name="test_skill",
            )
            save_cassette(skill_dir, cassette)

        cassettes = list_cassettes(skill_dir)

        assert len(cassettes) == 3
        fixture_names = {c["fixture_name"] for c in cassettes}
        assert fixture_names == {"fixture1", "fixture2", "fixture3"}


class TestCassetteIntegration:
    """Integration tests for cassette record and replay."""

    def test_record_then_replay(self, tmp_path):
        """Test recording and then replaying a cassette."""
        from skillforge.runner import run_skill

        skill_dir = create_test_skill(tmp_path, {
            "name": "test_skill",
            "inputs": [{"name": "target_dir", "type": "path"}],
            "steps": [
                {"id": "step1", "type": "shell", "command": "echo integration_test"},
            ],
            "checks": [],
        })
        create_fixture(skill_dir, "happy_path", {"test.txt": "test"})

        # Record
        record_result = record_cassette(skill_dir, "happy_path")
        assert record_result.success is True

        # Load and replay
        cassette = load_cassette(skill_dir, "happy_path")
        fixture_dir = skill_dir / "fixtures" / "happy_path"
        input_dir = fixture_dir / "input"

        report = run_skill(
            skill_dir=skill_dir,
            target_dir=input_dir,
            no_sandbox=True,
            cassette=cassette,
        )

        assert report.success is True
        assert report.mode == "cassette_replay"
        # The stdout should be from the cassette
        assert "integration_test" in report.steps[0].get("stdout", "")
