"""Record shell sessions to create skills from interactive work."""

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import yaml


@dataclass
class RecordedCommand:
    """A command recorded during a session."""

    command: str
    cwd: str
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    timestamp: str = ""
    duration_ms: int = 0
    files_changed: list[str] = field(default_factory=list)


@dataclass
class RecordingSession:
    """A recording session."""

    session_id: str
    name: str
    workdir: str
    mode: str = "git"
    shell: str = "bash"
    started_at: str = ""
    stopped_at: str = ""
    commands: list[RecordedCommand] = field(default_factory=list)
    initial_files: list[str] = field(default_factory=list)
    final_files: list[str] = field(default_factory=list)
    status: str = "active"  # active, stopped, compiled


@dataclass
class RecordResult:
    """Result of starting a recording."""

    success: bool = False
    error_message: str = ""
    session_id: str = ""
    session_dir: str = ""
    shell_command: str = ""


@dataclass
class StopResult:
    """Result of stopping a recording."""

    success: bool = False
    error_message: str = ""
    session_id: str = ""
    commands_recorded: int = 0
    files_changed: int = 0


@dataclass
class CompileResult:
    """Result of compiling a recording."""

    success: bool = False
    error_message: str = ""
    skill_dir: str = ""
    steps_created: int = 0


class RecorderError(Exception):
    """Raised when recording operations fail."""

    pass


def get_recordings_dir() -> Path:
    """Get the recordings directory."""
    config_dir = Path.home() / ".skillforge"
    recordings_dir = config_dir / "recordings"
    recordings_dir.mkdir(parents=True, exist_ok=True)
    return recordings_dir


def get_session_dir(session_id: str) -> Path:
    """Get the directory for a specific session."""
    return get_recordings_dir() / session_id


def generate_session_id() -> str:
    """Generate a unique session ID."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return f"rec_{timestamp}"


def get_active_session() -> Optional[RecordingSession]:
    """Get the currently active recording session, if any."""
    recordings_dir = get_recordings_dir()

    # Check environment variable first (set when in recording shell)
    env_session_id = os.environ.get("SKILLFORGE_RECORDING_SESSION")
    if env_session_id:
        session_file = recordings_dir / env_session_id / "session.json"
        if session_file.exists():
            session = load_session(env_session_id)
            if session and session.status == "active":
                return session

    # Scan for active sessions
    for session_dir in recordings_dir.iterdir():
        if session_dir.is_dir():
            session_file = session_dir / "session.json"
            if session_file.exists():
                session = load_session(session_dir.name)
                if session and session.status == "active":
                    return session

    return None


def load_session(session_id: str) -> Optional[RecordingSession]:
    """Load a recording session from disk."""
    session_dir = get_session_dir(session_id)
    session_file = session_dir / "session.json"

    if not session_file.exists():
        return None

    try:
        with open(session_file) as f:
            data = json.load(f)

        commands = [
            RecordedCommand(**cmd) for cmd in data.get("commands", [])
        ]

        return RecordingSession(
            session_id=data["session_id"],
            name=data["name"],
            workdir=data["workdir"],
            mode=data.get("mode", "git"),
            shell=data.get("shell", "bash"),
            started_at=data.get("started_at", ""),
            stopped_at=data.get("stopped_at", ""),
            commands=commands,
            initial_files=data.get("initial_files", []),
            final_files=data.get("final_files", []),
            status=data.get("status", "active"),
        )
    except Exception:
        return None


def save_session(session: RecordingSession) -> None:
    """Save a recording session to disk."""
    session_dir = get_session_dir(session.session_id)
    session_dir.mkdir(parents=True, exist_ok=True)

    data = {
        "session_id": session.session_id,
        "name": session.name,
        "workdir": session.workdir,
        "mode": session.mode,
        "shell": session.shell,
        "started_at": session.started_at,
        "stopped_at": session.stopped_at,
        "commands": [
            {
                "command": cmd.command,
                "cwd": cmd.cwd,
                "exit_code": cmd.exit_code,
                "stdout": cmd.stdout,
                "stderr": cmd.stderr,
                "timestamp": cmd.timestamp,
                "duration_ms": cmd.duration_ms,
                "files_changed": cmd.files_changed,
            }
            for cmd in session.commands
        ],
        "initial_files": session.initial_files,
        "final_files": session.final_files,
        "status": session.status,
    }

    session_file = session_dir / "session.json"
    with open(session_file, "w") as f:
        json.dump(data, f, indent=2)


def list_files_in_dir(directory: Path, git_tracked_only: bool = False) -> list[str]:
    """List files in a directory."""
    files = []

    if git_tracked_only:
        # Use git ls-files if it's a git repo
        try:
            result = subprocess.run(
                ["git", "ls-files"],
                cwd=directory,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                files = [f for f in result.stdout.strip().split("\n") if f]
                return files
        except Exception:
            pass

    # Fall back to walking the directory
    try:
        for root, dirs, filenames in os.walk(directory):
            # Skip hidden directories and common non-relevant dirs
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in {"node_modules", "__pycache__", "venv", ".venv"}]

            for filename in filenames:
                if not filename.startswith("."):
                    rel_path = os.path.relpath(os.path.join(root, filename), directory)
                    files.append(rel_path)
    except Exception:
        pass

    return sorted(files)


def init_git_tracking(workdir: Path, session_dir: Path) -> bool:
    """Initialize git tracking for a working directory.

    Creates a snapshot of the initial state.
    """
    snapshot_dir = session_dir / "snapshots" / "initial"
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    # Check if workdir is already a git repo
    git_dir = workdir / ".git"
    is_git_repo = git_dir.exists()

    if is_git_repo:
        # Save current git status
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=workdir,
                capture_output=True,
                text=True,
            )
            status_file = session_dir / "git_status_initial.txt"
            status_file.write_text(result.stdout)

            # Get current HEAD commit
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=workdir,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                head_file = session_dir / "git_head_initial.txt"
                head_file.write_text(result.stdout.strip())
        except Exception:
            pass

    # Take a file listing snapshot
    files = list_files_in_dir(workdir, git_tracked_only=is_git_repo)
    files_list = session_dir / "files_initial.txt"
    files_list.write_text("\n".join(files))

    return True


def get_file_changes(workdir: Path, session_dir: Path) -> list[str]:
    """Get files that changed since recording started."""
    changed = []

    # Check if we have initial git status
    head_file = session_dir / "git_head_initial.txt"

    if head_file.exists():
        # Use git diff against initial commit
        initial_head = head_file.read_text().strip()
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", initial_head],
                cwd=workdir,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                changed = [f for f in result.stdout.strip().split("\n") if f]

            # Also include untracked files
            result = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard"],
                cwd=workdir,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                untracked = [f for f in result.stdout.strip().split("\n") if f]
                changed.extend(untracked)
        except Exception:
            pass
    else:
        # Compare file listings
        files_initial_path = session_dir / "files_initial.txt"
        if files_initial_path.exists():
            initial_files = set(files_initial_path.read_text().strip().split("\n"))
            current_files = set(list_files_in_dir(workdir))

            # New files
            changed = list(current_files - initial_files)

            # Modified files would need content comparison - skip for now

    return sorted(set(changed))


def create_recording_shell_rc(session: RecordingSession, session_dir: Path) -> Path:
    """Create a shell RC file that enables recording."""
    rc_file = session_dir / "recording.rc"

    # Create the history file for this session
    history_file = session_dir / "commands.history"
    history_file.touch()

    # Create the command log file
    command_log = session_dir / "commands.log"

    if session.shell == "bash":
        rc_content = f'''# SkillForge Recording Session: {session.name}
# Session ID: {session.session_id}

# Export session info
export SKILLFORGE_RECORDING_SESSION="{session.session_id}"
export SKILLFORGE_RECORDING_DIR="{session_dir}"
export SKILLFORGE_WORKDIR="{session.workdir}"

# Set up command history
export HISTFILE="{history_file}"
export HISTSIZE=10000
export HISTFILESIZE=10000
export HISTCONTROL=ignoredups
shopt -s histappend

# Set up command logging
export SKILLFORGE_CMD_LOG="{command_log}"

# Custom prompt to show recording
export PS1="[\\[\\033[1;31m\\]REC\\[\\033[0m\\] {session.name}] \\w\\$ "

# Log each command
skillforge_log_command() {{
    local cmd="$(history 1 | sed 's/^[ ]*[0-9]*[ ]*//')"
    local ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    if [ -n "$cmd" ] && [ "$cmd" != "exit" ]; then
        echo "$ts|$PWD|$cmd" >> "$SKILLFORGE_CMD_LOG"
    fi
}}
export PROMPT_COMMAND="skillforge_log_command"

# Welcome message
echo ""
echo "======================================"
echo "  SkillForge Recording Session"
echo "======================================"
echo "  Session: {session.name}"
echo "  Workdir: {session.workdir}"
echo ""
echo "  All commands will be recorded."
echo "  Type 'exit' or run 'skillforge stop'"
echo "  to end the recording session."
echo "======================================"
echo ""

# Change to workdir
cd "{session.workdir}"
'''
    elif session.shell == "zsh":
        rc_content = f'''# SkillForge Recording Session: {session.name}
# Session ID: {session.session_id}

# Export session info
export SKILLFORGE_RECORDING_SESSION="{session.session_id}"
export SKILLFORGE_RECORDING_DIR="{session_dir}"
export SKILLFORGE_WORKDIR="{session.workdir}"

# Set up command history
export HISTFILE="{history_file}"
export HISTSIZE=10000
export SAVEHIST=10000
setopt APPEND_HISTORY
setopt INC_APPEND_HISTORY

# Set up command logging
export SKILLFORGE_CMD_LOG="{command_log}"

# Custom prompt to show recording
export PS1="[%F{{red}}REC%f {session.name}] %~%# "

# Log each command using preexec
preexec() {{
    local cmd="$1"
    local ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    if [ -n "$cmd" ] && [ "$cmd" != "exit" ]; then
        echo "$ts|$PWD|$cmd" >> "$SKILLFORGE_CMD_LOG"
    fi
}}

# Welcome message
echo ""
echo "======================================"
echo "  SkillForge Recording Session"
echo "======================================"
echo "  Session: {session.name}"
echo "  Workdir: {session.workdir}"
echo ""
echo "  All commands will be recorded."
echo "  Type 'exit' or run 'skillforge stop'"
echo "  to end the recording session."
echo "======================================"
echo ""

# Change to workdir
cd "{session.workdir}"
'''
    else:
        raise RecorderError(f"Unsupported shell: {session.shell}")

    rc_file.write_text(rc_content)
    return rc_file


def start_recording(
    name: str,
    workdir: Path,
    mode: str = "git",
    shell: str = "bash",
) -> RecordResult:
    """Start a new recording session.

    Args:
        name: Name for the recording session
        workdir: Working directory to record in
        mode: Recording mode (currently only 'git' supported)
        shell: Shell to use (bash or zsh)

    Returns:
        RecordResult with session info and shell command to run
    """
    result = RecordResult()

    # Check for existing active session
    active = get_active_session()
    if active:
        result.error_message = f"Recording session already active: {active.name} ({active.session_id})"
        return result

    # Validate workdir
    workdir = workdir.resolve()
    if not workdir.exists():
        result.error_message = f"Working directory not found: {workdir}"
        return result

    if not workdir.is_dir():
        result.error_message = f"Not a directory: {workdir}"
        return result

    # Validate shell
    if shell not in ("bash", "zsh"):
        result.error_message = f"Unsupported shell: {shell}. Use 'bash' or 'zsh'."
        return result

    # Check if shell is available
    shell_path = shutil.which(shell)
    if not shell_path:
        result.error_message = f"Shell not found: {shell}"
        return result

    # Create session
    session_id = generate_session_id()
    session_dir = get_session_dir(session_id)
    session_dir.mkdir(parents=True, exist_ok=True)

    session = RecordingSession(
        session_id=session_id,
        name=name,
        workdir=str(workdir),
        mode=mode,
        shell=shell,
        started_at=datetime.now().isoformat(),
        initial_files=list_files_in_dir(workdir),
    )

    # Initialize git tracking
    init_git_tracking(workdir, session_dir)

    # Create shell RC file
    try:
        rc_file = create_recording_shell_rc(session, session_dir)
    except RecorderError as e:
        result.error_message = str(e)
        return result

    # Save session
    save_session(session)

    # Build shell command
    if shell == "bash":
        shell_command = f'{shell_path} --rcfile "{rc_file}" -i'
    else:  # zsh
        shell_command = f'ZDOTDIR="{session_dir}" {shell_path} -i'
        # For zsh, we need to create .zshrc in the session dir
        zshrc = session_dir / ".zshrc"
        zshrc.write_text(rc_file.read_text())

    result.success = True
    result.session_id = session_id
    result.session_dir = str(session_dir)
    result.shell_command = shell_command

    return result


def stop_recording(session_id: Optional[str] = None) -> StopResult:
    """Stop a recording session.

    Args:
        session_id: Optional specific session to stop (default: active session)

    Returns:
        StopResult with summary
    """
    result = StopResult()

    # Find session
    if session_id:
        session = load_session(session_id)
    else:
        session = get_active_session()

    if not session:
        result.error_message = "No active recording session found"
        return result

    if session.status != "active":
        result.error_message = f"Session is not active: {session.status}"
        return result

    session_dir = get_session_dir(session.session_id)
    workdir = Path(session.workdir)

    # Parse command log
    command_log = session_dir / "commands.log"
    if command_log.exists():
        session.commands = parse_command_log(command_log)

    # Get final file state
    session.final_files = list_files_in_dir(workdir)

    # Get file changes
    changed_files = get_file_changes(workdir, session_dir)

    # Update session
    session.stopped_at = datetime.now().isoformat()
    session.status = "stopped"

    # Save session
    save_session(session)

    result.success = True
    result.session_id = session.session_id
    result.commands_recorded = len(session.commands)
    result.files_changed = len(changed_files)

    return result


def parse_command_log(log_file: Path) -> list[RecordedCommand]:
    """Parse the command log file."""
    commands = []

    try:
        content = log_file.read_text()
        for line in content.strip().split("\n"):
            if not line:
                continue

            parts = line.split("|", 2)
            if len(parts) >= 3:
                timestamp, cwd, command = parts

                # Skip internal commands
                if command.startswith("skillforge_log_command"):
                    continue
                if command.strip() in ("", "exit"):
                    continue

                commands.append(RecordedCommand(
                    command=command,
                    cwd=cwd,
                    timestamp=timestamp,
                ))
    except Exception:
        pass

    return commands


def list_recordings() -> list[dict[str, Any]]:
    """List all recording sessions."""
    recordings = []
    recordings_dir = get_recordings_dir()

    for session_dir in sorted(recordings_dir.iterdir(), reverse=True):
        if session_dir.is_dir():
            session = load_session(session_dir.name)
            if session:
                recordings.append({
                    "session_id": session.session_id,
                    "name": session.name,
                    "workdir": session.workdir,
                    "status": session.status,
                    "started_at": session.started_at,
                    "stopped_at": session.stopped_at,
                    "commands_count": len(session.commands),
                })

    return recordings


def get_recording_info(session_id: str) -> Optional[dict[str, Any]]:
    """Get detailed info about a recording."""
    session = load_session(session_id)
    if not session:
        return None

    session_dir = get_session_dir(session_id)

    return {
        "session_id": session.session_id,
        "name": session.name,
        "workdir": session.workdir,
        "mode": session.mode,
        "shell": session.shell,
        "status": session.status,
        "started_at": session.started_at,
        "stopped_at": session.stopped_at,
        "commands": [
            {
                "command": cmd.command,
                "cwd": cmd.cwd,
                "timestamp": cmd.timestamp,
            }
            for cmd in session.commands
        ],
        "initial_files_count": len(session.initial_files),
        "final_files_count": len(session.final_files),
        "session_dir": str(session_dir),
    }


def compile_recording(
    session_id: str,
    output_dir: Path,
    skill_name: Optional[str] = None,
) -> CompileResult:
    """Compile a recording into a skill.

    Args:
        session_id: ID of the recording session
        output_dir: Directory to create skill in
        skill_name: Optional custom skill name (default: session name)

    Returns:
        CompileResult with skill directory
    """
    result = CompileResult()

    # Load session
    session = load_session(session_id)
    if not session:
        result.error_message = f"Recording not found: {session_id}"
        return result

    if session.status == "active":
        result.error_message = "Recording is still active. Run 'skillforge stop' first."
        return result

    if not session.commands:
        result.error_message = "Recording has no commands"
        return result

    # Determine skill name
    name = skill_name or session.name
    safe_name = _normalize_name(name)

    skill_dir = output_dir / safe_name
    skill_dir.mkdir(parents=True, exist_ok=True)

    # Create skill structure
    (skill_dir / "fixtures" / "happy_path" / "input").mkdir(parents=True, exist_ok=True)
    (skill_dir / "fixtures" / "happy_path" / "expected").mkdir(parents=True, exist_ok=True)
    (skill_dir / "reports").mkdir(parents=True, exist_ok=True)
    (skill_dir / "cassettes").mkdir(parents=True, exist_ok=True)

    # Generate skill.yaml
    skill_data = _generate_skill_from_recording(session)
    skill_yaml = skill_dir / "skill.yaml"
    with open(skill_yaml, "w") as f:
        yaml.dump(skill_data, f, default_flow_style=False, sort_keys=False)

    # Generate SKILL.txt
    skill_txt = skill_dir / "SKILL.txt"
    skill_txt.write_text(_generate_skill_txt_from_recording(session))

    # Generate checks.py
    checks_py = skill_dir / "checks.py"
    checks_py.write_text(_generate_checks_py(session.name))

    # Generate fixture.yaml
    fixture_yaml = skill_dir / "fixtures" / "happy_path" / "fixture.yaml"
    fixture_yaml.write_text(_generate_fixture_yaml())

    # Create .gitkeep files
    for gitkeep_dir in [
        skill_dir / "fixtures" / "happy_path" / "input",
        skill_dir / "fixtures" / "happy_path" / "expected",
        skill_dir / "reports",
        skill_dir / "cassettes",
    ]:
        (gitkeep_dir / ".gitkeep").write_text("")

    # Update session status
    session.status = "compiled"
    save_session(session)

    result.success = True
    result.skill_dir = str(skill_dir)
    result.steps_created = len(skill_data.get("steps", []))

    return result


def _normalize_name(name: str) -> str:
    """Normalize a name for use as directory name."""
    safe_name = "".join(c if c.isalnum() or c == "_" else "_" for c in name)
    safe_name = safe_name.strip("_").lower()
    while "__" in safe_name:
        safe_name = safe_name.replace("__", "_")
    return safe_name or "recorded_skill"


def _generate_skill_from_recording(session: RecordingSession) -> dict[str, Any]:
    """Generate skill.yaml data from a recording."""
    data: dict[str, Any] = {
        "name": _normalize_name(session.name),
        "version": "0.1.0",
        "description": f"Skill recorded from session: {session.name}",
    }

    # Metadata
    data["metadata"] = {
        "recorded_from": session.session_id,
        "recorded_at": session.started_at,
        "original_workdir": session.workdir,
    }

    # Standard inputs
    data["inputs"] = [
        {
            "name": "target_dir",
            "type": "path",
            "description": "Target directory to run the skill against",
            "required": True,
        },
    ]

    # Convert commands to steps
    data["steps"] = []
    workdir = session.workdir

    for i, cmd in enumerate(session.commands, 1):
        # Determine working directory relative to sandbox
        if cmd.cwd == workdir:
            cwd = "{sandbox_dir}"
        elif cmd.cwd.startswith(workdir):
            rel_path = os.path.relpath(cmd.cwd, workdir)
            cwd = "{sandbox_dir}/" + rel_path
        else:
            cwd = cmd.cwd

        step: dict[str, Any] = {
            "id": f"step{i}",
            "type": "shell",
            "name": _summarize_command(cmd.command),
            "command": cmd.command,
            "cwd": cwd,
        }

        data["steps"].append(step)

    # Add exit code checks for all steps
    data["checks"] = []
    for i in range(1, len(data["steps"]) + 1):
        data["checks"].append({
            "id": f"check{i}",
            "type": "exit_code",
            "step_id": f"step{i}",
            "equals": 0,
        })

    return data


def _summarize_command(command: str) -> str:
    """Create a short summary of a command for the step name."""
    # Get first word (the command name)
    parts = command.split()
    if not parts:
        return "Run command"

    cmd_name = parts[0]

    # Common command summaries
    summaries = {
        "cd": "Change directory",
        "ls": "List files",
        "cat": "View file",
        "echo": "Print output",
        "mkdir": "Create directory",
        "rm": "Remove files",
        "cp": "Copy files",
        "mv": "Move files",
        "touch": "Create file",
        "git": "Git operation",
        "npm": "NPM operation",
        "pip": "Pip operation",
        "python": "Run Python",
        "node": "Run Node",
        "make": "Run make",
        "cargo": "Cargo operation",
        "go": "Go operation",
        "docker": "Docker operation",
        "curl": "HTTP request",
        "wget": "Download file",
    }

    summary = summaries.get(cmd_name, f"Run {cmd_name}")

    # Add context for some commands
    if cmd_name == "git" and len(parts) > 1:
        summary = f"Git {parts[1]}"
    elif cmd_name in ("mkdir", "rm", "touch") and len(parts) > 1:
        target = parts[-1].split("/")[-1][:20]
        summary = f"{summaries.get(cmd_name, cmd_name)} {target}"

    return summary


def _generate_skill_txt_from_recording(session: RecordingSession) -> str:
    """Generate SKILL.txt content from a recording."""
    lines = [
        f"SKILL: {_normalize_name(session.name)}",
        "=" * (7 + len(_normalize_name(session.name))),
        "",
        "DESCRIPTION",
        "-----------",
        f"Skill recorded from session: {session.name}",
        f"Recorded at: {session.started_at}",
        f"Original workdir: {session.workdir}",
        "",
        "INPUTS",
        "------",
        "- target_dir: path (required) - Target directory",
        "",
        "STEPS",
        "-----",
    ]

    for i, cmd in enumerate(session.commands, 1):
        summary = _summarize_command(cmd.command)
        lines.append(f"{i}. {summary}")

        # Show command (truncated)
        cmd_display = cmd.command
        if len(cmd_display) > 60:
            cmd_display = cmd_display[:57] + "..."
        lines.append(f"   - Run: {cmd_display}")

    lines.extend([
        "",
        "CHECKS",
        "------",
    ])

    for i in range(1, len(session.commands) + 1):
        lines.append(f"- Step {i} exits with code 0")

    lines.append("")

    return "\n".join(lines)


def _generate_checks_py(name: str) -> str:
    """Generate checks.py content."""
    return f'''"""Custom checks for the {name} skill."""

from pathlib import Path
from typing import Any


def custom_check(context: dict[str, Any]) -> tuple[bool, str]:
    """Example custom check function.

    Args:
        context: Dictionary containing:
            - target_dir: Path to the target directory
            - sandbox_dir: Path to the sandbox directory
            - inputs: Resolved input values
            - step_results: Results from executed steps

    Returns:
        Tuple of (success: bool, message: str)
    """
    # Placeholder - always passes
    return True, "Custom check passed"


# Add more custom check functions as needed
'''


def _generate_fixture_yaml() -> str:
    """Generate fixture.yaml content."""
    return """# Fixture configuration
# Override skill inputs for this fixture

# inputs:
#   target_dir: "."

# allow_extra_files: false
"""


def delete_recording(session_id: str) -> bool:
    """Delete a recording session."""
    session_dir = get_session_dir(session_id)
    if session_dir.exists():
        shutil.rmtree(session_dir)
        return True
    return False
