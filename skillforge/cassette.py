"""Cassette recording and replay for deterministic testing."""

import hashlib
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import yaml

from skillforge.executor import StepResult


@dataclass
class RecordedCommand:
    """A recorded command execution."""

    step_id: str
    command: str
    cwd: str = ""
    env_hash: str = ""  # Hash of relevant env vars for matching
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    duration_ms: int = 0


@dataclass
class Cassette:
    """A cassette containing recorded command outputs."""

    fixture_name: str
    skill_name: str = ""
    recorded_at: str = ""
    commands: list[RecordedCommand] = field(default_factory=list)

    def find_command(self, step_id: str, command: str, cwd: str = "") -> Optional[RecordedCommand]:
        """Find a recorded command by step_id and command string.

        Args:
            step_id: The step ID to match
            command: The command string to match
            cwd: Optional working directory to match

        Returns:
            RecordedCommand if found, None otherwise
        """
        for recorded in self.commands:
            if recorded.step_id == step_id and recorded.command == command:
                # If cwd is specified, it should match too
                if cwd and recorded.cwd and recorded.cwd != cwd:
                    continue
                return recorded
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert cassette to dictionary for YAML serialization."""
        return {
            "fixture_name": self.fixture_name,
            "skill_name": self.skill_name,
            "recorded_at": self.recorded_at,
            "commands": [
                {
                    "step_id": cmd.step_id,
                    "command": cmd.command,
                    "cwd": cmd.cwd,
                    "exit_code": cmd.exit_code,
                    "stdout": cmd.stdout,
                    "stderr": cmd.stderr,
                    "duration_ms": cmd.duration_ms,
                }
                for cmd in self.commands
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Cassette":
        """Create cassette from dictionary."""
        cassette = cls(
            fixture_name=data.get("fixture_name", ""),
            skill_name=data.get("skill_name", ""),
            recorded_at=data.get("recorded_at", ""),
        )
        for cmd_data in data.get("commands", []):
            cassette.commands.append(
                RecordedCommand(
                    step_id=cmd_data.get("step_id", ""),
                    command=cmd_data.get("command", ""),
                    cwd=cmd_data.get("cwd", ""),
                    exit_code=cmd_data.get("exit_code", 0),
                    stdout=cmd_data.get("stdout", ""),
                    stderr=cmd_data.get("stderr", ""),
                    duration_ms=cmd_data.get("duration_ms", 0),
                )
            )
        return cassette


@dataclass
class CassetteRecordResult:
    """Result of recording a cassette."""

    success: bool = False
    error_message: str = ""
    cassette_path: str = ""
    commands_recorded: int = 0


@dataclass
class CassetteReplayResult:
    """Result of replaying with a cassette."""

    success: bool = False
    error_message: str = ""
    commands_replayed: int = 0
    commands_missed: list[str] = field(default_factory=list)


def get_cassette_path(skill_dir: Path, fixture_name: str) -> Path:
    """Get the path to a cassette file.

    Args:
        skill_dir: Path to the skill directory
        fixture_name: Name of the fixture

    Returns:
        Path to the cassette YAML file
    """
    return skill_dir / "cassettes" / f"{fixture_name}.yaml"


def load_cassette(skill_dir: Path, fixture_name: str) -> Optional[Cassette]:
    """Load a cassette from disk.

    Args:
        skill_dir: Path to the skill directory
        fixture_name: Name of the fixture

    Returns:
        Cassette if found, None otherwise
    """
    cassette_path = get_cassette_path(skill_dir, fixture_name)
    if not cassette_path.exists():
        return None

    try:
        with open(cassette_path) as f:
            data = yaml.safe_load(f)
        return Cassette.from_dict(data)
    except Exception:
        return None


def save_cassette(skill_dir: Path, cassette: Cassette) -> Path:
    """Save a cassette to disk.

    Args:
        skill_dir: Path to the skill directory
        cassette: Cassette to save

    Returns:
        Path to the saved cassette file
    """
    cassettes_dir = skill_dir / "cassettes"
    cassettes_dir.mkdir(parents=True, exist_ok=True)

    cassette_path = cassettes_dir / f"{cassette.fixture_name}.yaml"
    with open(cassette_path, "w") as f:
        yaml.dump(cassette.to_dict(), f, default_flow_style=False, sort_keys=False)

    return cassette_path


def record_cassette(
    skill_dir: Path,
    fixture_name: str,
) -> CassetteRecordResult:
    """Record a cassette by running a skill and capturing command outputs.

    Args:
        skill_dir: Path to the skill directory
        fixture_name: Name of the fixture to record

    Returns:
        CassetteRecordResult with outcome details
    """
    from skillforge.runner import run_skill
    from skillforge.loader import load_skill_yaml
    from skillforge.sandbox import generate_run_id

    result = CassetteRecordResult()

    # Validate fixture exists
    fixture_dir = skill_dir / "fixtures" / fixture_name
    if not fixture_dir.is_dir():
        result.error_message = f"Fixture not found: {fixture_name}"
        return result

    input_dir = fixture_dir / "input"
    if not input_dir.is_dir():
        result.error_message = f"Fixture input directory not found: {input_dir}"
        return result

    # Load skill info
    try:
        skill_data = load_skill_yaml(skill_dir)
        skill_name = skill_data.get("name", "unknown")
    except Exception as e:
        result.error_message = f"Failed to load skill: {e}"
        return result

    # Run the skill
    run_id = generate_run_id()
    sandbox_dir = skill_dir / "reports" / f"cassette_{run_id}" / fixture_name / "sandbox"

    try:
        report = run_skill(
            skill_dir=skill_dir,
            target_dir=input_dir,
            sandbox_dir=sandbox_dir,
            no_sandbox=False,
        )

        if not report.success:
            result.error_message = f"Skill execution failed: {report.error_message}"
            return result

        # Create cassette from step results
        cassette = Cassette(
            fixture_name=fixture_name,
            skill_name=skill_name,
            recorded_at=datetime.now().isoformat(),
        )

        for step in report.steps:
            if step.get("type") == "shell":
                cassette.commands.append(
                    RecordedCommand(
                        step_id=step.get("id", ""),
                        command=step.get("command", ""),
                        cwd=step.get("cwd", ""),
                        exit_code=step.get("exit_code", 0),
                        stdout=step.get("stdout", ""),
                        stderr=step.get("stderr", ""),
                        duration_ms=step.get("duration_ms", 0),
                    )
                )

        # Save cassette
        cassette_path = save_cassette(skill_dir, cassette)

        result.success = True
        result.cassette_path = str(cassette_path)
        result.commands_recorded = len(cassette.commands)

    except Exception as e:
        result.error_message = str(e)

    return result


def replay_step_from_cassette(
    cassette: Cassette,
    step_id: str,
    command: str,
    cwd: str = "",
) -> Optional[StepResult]:
    """Replay a step from a cassette.

    Args:
        cassette: The cassette to replay from
        step_id: The step ID
        command: The command string
        cwd: The working directory

    Returns:
        StepResult with recorded output, or None if not found
    """
    recorded = cassette.find_command(step_id, command, cwd)
    if not recorded:
        return None

    return StepResult(
        step_id=step_id,
        step_type="shell",
        status="success" if recorded.exit_code == 0 else "failed",
        exit_code=recorded.exit_code,
        stdout=recorded.stdout,
        stderr=recorded.stderr,
        duration_ms=recorded.duration_ms,
        resolved_command=command,
        resolved_cwd=cwd,
    )


def get_cassette_info(skill_dir: Path, fixture_name: str) -> dict[str, Any]:
    """Get information about an existing cassette.

    Args:
        skill_dir: Path to the skill directory
        fixture_name: Name of the fixture

    Returns:
        Dictionary with cassette info, or empty dict if none exists
    """
    cassette = load_cassette(skill_dir, fixture_name)
    if not cassette:
        return {}

    return {
        "exists": True,
        "path": str(get_cassette_path(skill_dir, fixture_name)),
        "fixture_name": cassette.fixture_name,
        "skill_name": cassette.skill_name,
        "recorded_at": cassette.recorded_at,
        "commands_count": len(cassette.commands),
        "commands": [
            {
                "step_id": cmd.step_id,
                "command": cmd.command[:50] + "..." if len(cmd.command) > 50 else cmd.command,
            }
            for cmd in cassette.commands
        ],
    }


def list_cassettes(skill_dir: Path) -> list[dict[str, Any]]:
    """List all cassettes for a skill.

    Args:
        skill_dir: Path to the skill directory

    Returns:
        List of cassette info dictionaries
    """
    cassettes_dir = skill_dir / "cassettes"
    if not cassettes_dir.is_dir():
        return []

    cassettes = []
    for cassette_file in sorted(cassettes_dir.glob("*.yaml")):
        fixture_name = cassette_file.stem
        info = get_cassette_info(skill_dir, fixture_name)
        if info:
            cassettes.append(info)

    return cassettes
