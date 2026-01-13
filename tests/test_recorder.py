"""Tests for the recorder module."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from skillforge.recorder import (
    RecordedCommand,
    RecordingSession,
    RecordResult,
    StopResult,
    CompileResult,
    generate_session_id,
    get_recordings_dir,
    get_session_dir,
    save_session,
    load_session,
    list_files_in_dir,
    parse_command_log,
    list_recordings,
    get_recording_info,
    compile_recording,
    delete_recording,
    _normalize_name,
    _summarize_command,
    _generate_skill_from_recording,
    _generate_skill_txt_from_recording,
)


class TestGenerateSessionId:
    """Tests for generate_session_id function."""

    def test_generates_unique_ids(self):
        """Test that session IDs are unique."""
        ids = [generate_session_id() for _ in range(5)]
        assert len(set(ids)) == 5

    def test_id_format(self):
        """Test session ID format."""
        session_id = generate_session_id()
        assert session_id.startswith("rec_")
        assert len(session_id) > 10


class TestRecordingsDir:
    """Tests for recordings directory functions."""

    def test_get_recordings_dir_creates_dir(self, tmp_path, monkeypatch):
        """Test that get_recordings_dir creates the directory."""
        # Monkeypatch home directory
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        recordings_dir = get_recordings_dir()
        assert recordings_dir.exists()
        assert recordings_dir == tmp_path / ".skillforge" / "recordings"

    def test_get_session_dir(self, tmp_path, monkeypatch):
        """Test get_session_dir returns correct path."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        session_dir = get_session_dir("rec_test_123")
        assert session_dir == tmp_path / ".skillforge" / "recordings" / "rec_test_123"


class TestSaveLoadSession:
    """Tests for saving and loading sessions."""

    def test_save_and_load_session(self, tmp_path, monkeypatch):
        """Test saving and loading a session."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        session = RecordingSession(
            session_id="rec_test_001",
            name="test_session",
            workdir="/tmp/test",
            mode="git",
            shell="bash",
            started_at="2024-01-15T10:00:00",
            status="active",
            commands=[
                RecordedCommand(
                    command="echo hello",
                    cwd="/tmp/test",
                    exit_code=0,
                    timestamp="2024-01-15T10:01:00",
                ),
            ],
        )

        save_session(session)

        # Verify file was created
        session_file = get_session_dir("rec_test_001") / "session.json"
        assert session_file.exists()

        # Load and verify
        loaded = load_session("rec_test_001")
        assert loaded is not None
        assert loaded.session_id == "rec_test_001"
        assert loaded.name == "test_session"
        assert loaded.workdir == "/tmp/test"
        assert loaded.shell == "bash"
        assert loaded.status == "active"
        assert len(loaded.commands) == 1
        assert loaded.commands[0].command == "echo hello"

    def test_load_nonexistent_session(self, tmp_path, monkeypatch):
        """Test loading a session that doesn't exist."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        loaded = load_session("nonexistent")
        assert loaded is None


class TestListFilesInDir:
    """Tests for list_files_in_dir function."""

    def test_list_files_simple(self, tmp_path):
        """Test listing files in a directory."""
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.py").write_text("content2")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "file3.txt").write_text("content3")

        files = list_files_in_dir(tmp_path)
        assert "file1.txt" in files
        assert "file2.py" in files
        assert any("file3.txt" in f for f in files)

    def test_list_files_skips_hidden(self, tmp_path):
        """Test that hidden files and directories are skipped."""
        (tmp_path / "visible.txt").write_text("content")
        (tmp_path / ".hidden").write_text("hidden")
        (tmp_path / ".hidden_dir").mkdir()
        (tmp_path / ".hidden_dir" / "file.txt").write_text("content")

        files = list_files_in_dir(tmp_path)
        assert "visible.txt" in files
        assert ".hidden" not in files
        assert not any(".hidden_dir" in f for f in files)

    def test_list_files_skips_node_modules(self, tmp_path):
        """Test that node_modules is skipped."""
        (tmp_path / "index.js").write_text("content")
        (tmp_path / "node_modules").mkdir()
        (tmp_path / "node_modules" / "dep.js").write_text("content")

        files = list_files_in_dir(tmp_path)
        assert "index.js" in files
        assert not any("node_modules" in f for f in files)


class TestParseCommandLog:
    """Tests for parse_command_log function."""

    def test_parse_command_log(self, tmp_path):
        """Test parsing a command log file."""
        log_file = tmp_path / "commands.log"
        log_file.write_text(
            "2024-01-15T10:00:00Z|/tmp/test|echo hello\n"
            "2024-01-15T10:01:00Z|/tmp/test/subdir|ls -la\n"
            "2024-01-15T10:02:00Z|/tmp/test|git status\n"
        )

        commands = parse_command_log(log_file)
        assert len(commands) == 3
        assert commands[0].command == "echo hello"
        assert commands[0].cwd == "/tmp/test"
        assert commands[0].timestamp == "2024-01-15T10:00:00Z"
        assert commands[1].command == "ls -la"
        assert commands[2].command == "git status"

    def test_parse_command_log_skips_empty_lines(self, tmp_path):
        """Test that empty lines are skipped."""
        log_file = tmp_path / "commands.log"
        log_file.write_text(
            "2024-01-15T10:00:00Z|/tmp/test|echo hello\n"
            "\n"
            "2024-01-15T10:01:00Z|/tmp/test|ls\n"
        )

        commands = parse_command_log(log_file)
        assert len(commands) == 2

    def test_parse_command_log_skips_exit(self, tmp_path):
        """Test that exit command is skipped."""
        log_file = tmp_path / "commands.log"
        log_file.write_text(
            "2024-01-15T10:00:00Z|/tmp/test|echo hello\n"
            "2024-01-15T10:01:00Z|/tmp/test|exit\n"
        )

        commands = parse_command_log(log_file)
        assert len(commands) == 1
        assert commands[0].command == "echo hello"


class TestListRecordings:
    """Tests for list_recordings function."""

    def test_list_recordings_empty(self, tmp_path, monkeypatch):
        """Test listing recordings when none exist."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        recordings = list_recordings()
        assert recordings == []

    def test_list_recordings(self, tmp_path, monkeypatch):
        """Test listing multiple recordings."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Create some sessions
        for i, status in enumerate(["active", "stopped", "compiled"]):
            session = RecordingSession(
                session_id=f"rec_test_{i:03d}",
                name=f"session_{i}",
                workdir="/tmp/test",
                status=status,
                started_at=f"2024-01-15T{10+i:02d}:00:00",
            )
            save_session(session)

        recordings = list_recordings()
        assert len(recordings) == 3

        # Check they have the expected fields
        for rec in recordings:
            assert "session_id" in rec
            assert "name" in rec
            assert "status" in rec


class TestGetRecordingInfo:
    """Tests for get_recording_info function."""

    def test_get_recording_info(self, tmp_path, monkeypatch):
        """Test getting detailed info about a recording."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        session = RecordingSession(
            session_id="rec_test_info",
            name="info_test",
            workdir="/tmp/test",
            mode="git",
            shell="bash",
            started_at="2024-01-15T10:00:00",
            status="stopped",
            commands=[
                RecordedCommand(command="echo one", cwd="/tmp/test"),
                RecordedCommand(command="echo two", cwd="/tmp/test"),
            ],
        )
        save_session(session)

        info = get_recording_info("rec_test_info")
        assert info is not None
        assert info["session_id"] == "rec_test_info"
        assert info["name"] == "info_test"
        assert info["status"] == "stopped"
        assert len(info["commands"]) == 2

    def test_get_recording_info_not_found(self, tmp_path, monkeypatch):
        """Test getting info for nonexistent recording."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        info = get_recording_info("nonexistent")
        assert info is None


class TestNormalizeName:
    """Tests for _normalize_name function."""

    def test_normalize_simple(self):
        """Test normalizing a simple name."""
        assert _normalize_name("deploy") == "deploy"

    def test_normalize_with_spaces(self):
        """Test normalizing name with spaces."""
        assert _normalize_name("my deploy script") == "my_deploy_script"

    def test_normalize_with_special_chars(self):
        """Test normalizing name with special characters."""
        assert _normalize_name("deploy-v2!@#") == "deploy_v2"

    def test_normalize_collapses_underscores(self):
        """Test that multiple underscores are collapsed."""
        assert _normalize_name("a__b___c") == "a_b_c"

    def test_normalize_empty_returns_default(self):
        """Test that empty name returns default."""
        assert _normalize_name("") == "recorded_skill"
        assert _normalize_name("!@#$%") == "recorded_skill"


class TestSummarizeCommand:
    """Tests for _summarize_command function."""

    def test_summarize_common_commands(self):
        """Test summarizing common commands."""
        assert _summarize_command("cd /tmp") == "Change directory"
        assert _summarize_command("ls -la") == "List files"
        assert _summarize_command("echo hello") == "Print output"

    def test_summarize_git_commands(self):
        """Test summarizing git commands."""
        assert _summarize_command("git status") == "Git status"
        assert _summarize_command("git add .") == "Git add"
        assert _summarize_command("git commit -m 'msg'") == "Git commit"

    def test_summarize_unknown_command(self):
        """Test summarizing unknown commands."""
        assert _summarize_command("mycustomcmd arg") == "Run mycustomcmd"

    def test_summarize_empty_command(self):
        """Test summarizing empty command."""
        assert _summarize_command("") == "Run command"


class TestCompileRecording:
    """Tests for compile_recording function."""

    def test_compile_recording_not_found(self, tmp_path, monkeypatch):
        """Test compiling nonexistent recording."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        result = compile_recording("nonexistent", tmp_path / "skills")
        assert not result.success
        assert "not found" in result.error_message

    def test_compile_active_recording(self, tmp_path, monkeypatch):
        """Test compiling active recording fails."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        session = RecordingSession(
            session_id="rec_active",
            name="active_test",
            workdir="/tmp/test",
            status="active",
            commands=[RecordedCommand(command="echo test", cwd="/tmp/test")],
        )
        save_session(session)

        result = compile_recording("rec_active", tmp_path / "skills")
        assert not result.success
        assert "still active" in result.error_message

    def test_compile_recording_no_commands(self, tmp_path, monkeypatch):
        """Test compiling recording with no commands."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        session = RecordingSession(
            session_id="rec_empty",
            name="empty_test",
            workdir="/tmp/test",
            status="stopped",
            commands=[],
        )
        save_session(session)

        result = compile_recording("rec_empty", tmp_path / "skills")
        assert not result.success
        assert "no commands" in result.error_message

    def test_compile_recording_success(self, tmp_path, monkeypatch):
        """Test successful compilation."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        session = RecordingSession(
            session_id="rec_compile",
            name="compile_test",
            workdir="/tmp/testworkdir",
            status="stopped",
            started_at="2024-01-15T10:00:00",
            commands=[
                RecordedCommand(command="mkdir subdir", cwd="/tmp/testworkdir"),
                RecordedCommand(command="touch subdir/file.txt", cwd="/tmp/testworkdir"),
                RecordedCommand(command="echo hello", cwd="/tmp/testworkdir/subdir"),
            ],
        )
        save_session(session)

        output_dir = tmp_path / "skills"
        result = compile_recording("rec_compile", output_dir)

        assert result.success
        assert result.steps_created == 3

        # Verify skill directory structure
        skill_dir = output_dir / "compile_test"
        assert skill_dir.exists()
        assert (skill_dir / "skill.yaml").exists()
        assert (skill_dir / "SKILL.txt").exists()
        assert (skill_dir / "checks.py").exists()
        assert (skill_dir / "fixtures" / "happy_path").exists()

        # Verify skill.yaml content
        with open(skill_dir / "skill.yaml") as f:
            skill_data = yaml.safe_load(f)

        assert skill_data["name"] == "compile_test"
        assert len(skill_data["steps"]) == 3
        assert skill_data["steps"][0]["command"] == "mkdir subdir"
        assert skill_data["steps"][2]["cwd"] == "{sandbox_dir}/subdir"

        # Verify checks were created
        assert len(skill_data["checks"]) == 3

    def test_compile_with_custom_name(self, tmp_path, monkeypatch):
        """Test compilation with custom skill name."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        session = RecordingSession(
            session_id="rec_custom",
            name="original_name",
            workdir="/tmp/test",
            status="stopped",
            commands=[RecordedCommand(command="echo test", cwd="/tmp/test")],
        )
        save_session(session)

        output_dir = tmp_path / "skills"
        result = compile_recording("rec_custom", output_dir, skill_name="custom_skill")

        assert result.success
        assert (output_dir / "custom_skill").exists()


class TestGenerateSkillFromRecording:
    """Tests for _generate_skill_from_recording function."""

    def test_generate_skill_data(self):
        """Test generating skill data from a recording."""
        session = RecordingSession(
            session_id="rec_test",
            name="test_skill",
            workdir="/home/user/project",
            started_at="2024-01-15T10:00:00",
            commands=[
                RecordedCommand(command="npm install", cwd="/home/user/project"),
                RecordedCommand(command="npm run build", cwd="/home/user/project"),
            ],
        )

        data = _generate_skill_from_recording(session)

        assert data["name"] == "test_skill"
        assert "description" in data
        assert data["metadata"]["recorded_from"] == "rec_test"
        assert len(data["steps"]) == 2
        assert data["steps"][0]["command"] == "npm install"
        assert data["steps"][0]["cwd"] == "{sandbox_dir}"
        assert len(data["checks"]) == 2


class TestGenerateSkillTxt:
    """Tests for _generate_skill_txt_from_recording function."""

    def test_generate_skill_txt(self):
        """Test generating SKILL.txt content."""
        session = RecordingSession(
            session_id="rec_test",
            name="my_skill",
            workdir="/home/user/project",
            started_at="2024-01-15T10:00:00",
            commands=[
                RecordedCommand(command="npm install", cwd="/home/user/project"),
                RecordedCommand(command="npm run build", cwd="/home/user/project"),
            ],
        )

        content = _generate_skill_txt_from_recording(session)

        assert "SKILL: my_skill" in content
        assert "DESCRIPTION" in content
        assert "INPUTS" in content
        assert "STEPS" in content
        assert "npm install" in content
        assert "npm run build" in content


class TestDeleteRecording:
    """Tests for delete_recording function."""

    def test_delete_recording(self, tmp_path, monkeypatch):
        """Test deleting a recording."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        session = RecordingSession(
            session_id="rec_delete",
            name="delete_test",
            workdir="/tmp/test",
            status="stopped",
        )
        save_session(session)

        # Verify it exists
        assert load_session("rec_delete") is not None

        # Delete
        result = delete_recording("rec_delete")
        assert result is True

        # Verify it's gone
        assert load_session("rec_delete") is None

    def test_delete_nonexistent_recording(self, tmp_path, monkeypatch):
        """Test deleting a recording that doesn't exist."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        result = delete_recording("nonexistent")
        assert result is False


class TestCLIIntegration:
    """Tests for CLI integration with recorder."""

    def test_recording_list_empty(self, tmp_path, monkeypatch):
        """Test recording list with no recordings."""
        from typer.testing import CliRunner
        from skillforge.cli import app

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        runner = CliRunner()
        result = runner.invoke(app, ["recording", "list"])

        assert result.exit_code == 0
        assert "No recordings found" in result.output

    def test_recording_show_not_found(self, tmp_path, monkeypatch):
        """Test recording show with nonexistent recording."""
        from typer.testing import CliRunner
        from skillforge.cli import app

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        runner = CliRunner()
        result = runner.invoke(app, ["recording", "show", "nonexistent"])

        assert result.exit_code == 1
        assert "not found" in result.output

    def test_stop_no_active_session(self, tmp_path, monkeypatch):
        """Test stop command with no active session."""
        from typer.testing import CliRunner
        from skillforge.cli import app

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        runner = CliRunner()
        result = runner.invoke(app, ["stop"])

        assert result.exit_code == 0
        assert "No active recording session" in result.output

    def test_compile_not_found(self, tmp_path, monkeypatch):
        """Test compile command with nonexistent recording."""
        from typer.testing import CliRunner
        from skillforge.cli import app

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        runner = CliRunner()
        result = runner.invoke(app, ["compile", "nonexistent"])

        assert result.exit_code == 1
        assert "not found" in result.output

    def test_compile_success(self, tmp_path, monkeypatch):
        """Test successful compile command."""
        from typer.testing import CliRunner
        from skillforge.cli import app

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Create a stopped session
        session = RecordingSession(
            session_id="rec_cli_test",
            name="cli_test",
            workdir="/tmp/test",
            status="stopped",
            started_at="2024-01-15T10:00:00",
            commands=[
                RecordedCommand(command="echo hello", cwd="/tmp/test"),
            ],
        )
        save_session(session)

        output_dir = tmp_path / "skills"
        output_dir.mkdir()

        runner = CliRunner()
        result = runner.invoke(app, ["compile", "rec_cli_test", "--out", str(output_dir)])

        assert result.exit_code == 0
        assert "compiled successfully" in result.output
        assert (output_dir / "cli_test" / "skill.yaml").exists()
