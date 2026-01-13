"""Skill runner - orchestrates skill execution."""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from skillforge.checks import CheckResult, execute_check
from skillforge.executor import StepResult, execute_step
from skillforge.loader import load_skill_yaml, SkillLoadError
from skillforge.placeholders import build_context, PlaceholderError
from skillforge.sandbox import (
    create_sandbox,
    generate_run_id,
    get_reports_path,
    get_sandbox_path,
    load_ignore_patterns,
    SandboxError,
)
from skillforge.secrets import (
    SecretManager,
    SecretMasker,
    SecretNotFoundError,
    get_secret_manager,
)


@dataclass
class RunReport:
    """Complete report of a skill run."""

    run_id: str
    skill_name: str
    skill_dir: str
    started_at: str
    finished_at: str = ""
    mode: str = "run"  # run, test, bless, cassette_record, cassette_replay
    target_original_path: str = ""
    sandbox_path: str = ""
    inputs_resolved: dict[str, Any] = field(default_factory=dict)
    steps: list[dict[str, Any]] = field(default_factory=list)
    checks: list[dict[str, Any]] = field(default_factory=list)
    success: bool = False
    failed_step_id: Optional[str] = None
    error_message: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class RunError(Exception):
    """Raised when skill execution fails."""

    pass


def run_skill(
    skill_dir: Path,
    target_dir: Path,
    sandbox_dir: Optional[Path] = None,
    no_sandbox: bool = False,
    dry_run: bool = False,
    env_vars: Optional[dict[str, str]] = None,
    input_overrides: Optional[dict[str, Any]] = None,
    cassette: Optional[Any] = None,  # Cassette object for replay mode
    secret_manager: Optional[SecretManager] = None,
    mask_secrets: bool = True,
) -> RunReport:
    """Run a skill against a target directory.

    Args:
        skill_dir: Path to the skill directory
        target_dir: Path to the target directory
        sandbox_dir: Optional custom sandbox directory
        no_sandbox: If True, run directly in target (dangerous)
        dry_run: If True, print plan without executing
        env_vars: Additional environment variables
        input_overrides: Override input values
        cassette: Optional Cassette object for replay mode
        secret_manager: Optional SecretManager for resolving {secret:name} placeholders
        mask_secrets: If True, mask secret values in logs and reports

    Returns:
        RunReport with execution details

    Raises:
        RunError: If execution fails at setup stage
    """
    run_id = generate_run_id()
    started_at = datetime.now().isoformat()

    # Determine mode
    if dry_run:
        mode = "dry_run"
    elif cassette is not None:
        mode = "cassette_replay"
    else:
        mode = "run"

    # Initialize secret manager and masker
    if secret_manager is None:
        secret_manager = get_secret_manager()

    masker: Optional[SecretMasker] = None
    if mask_secrets:
        masker = SecretMasker()
        masker.add_from_manager(secret_manager)

    # Initialize report
    report = RunReport(
        run_id=run_id,
        skill_name="",
        skill_dir=str(skill_dir),
        started_at=started_at,
        target_original_path=str(target_dir),
        mode=mode,
    )

    try:
        # Load skill
        skill_data = load_skill_yaml(skill_dir)
        report.skill_name = skill_data.get("name", "unknown")

        # Resolve inputs
        inputs = _resolve_inputs(skill_data, target_dir, input_overrides)
        report.inputs_resolved = inputs

        # Setup sandbox
        if no_sandbox:
            sandbox = target_dir
            report.sandbox_path = str(target_dir)
        elif sandbox_dir:
            sandbox = sandbox_dir
            report.sandbox_path = str(sandbox_dir)
            if not dry_run:
                ignore_patterns = load_ignore_patterns(skill_dir, target_dir)
                create_sandbox(target_dir, sandbox, ignore_patterns)
        else:
            sandbox = get_sandbox_path(skill_dir, run_id)
            report.sandbox_path = str(sandbox)
            if not dry_run:
                ignore_patterns = load_ignore_patterns(skill_dir, target_dir)
                create_sandbox(target_dir, sandbox, ignore_patterns)

        # Setup reports directory
        reports_dir = get_reports_path(skill_dir, run_id)
        logs_dir = reports_dir / "logs"
        if not dry_run:
            logs_dir.mkdir(parents=True, exist_ok=True)

        # Build context for placeholder substitution
        context = build_context(
            target_dir=str(target_dir),
            sandbox_dir=str(sandbox),
            inputs=inputs,
        )

        # Add env vars to context
        if env_vars:
            context.update(env_vars)

        # Execute steps
        steps = skill_data.get("steps", [])
        step_results: dict[str, StepResult] = {}

        for step in steps:
            step_id = step.get("id", "unknown")
            step_type = step.get("type", "")

            # Try cassette replay for shell steps
            result = None
            if cassette is not None and step_type == "shell":
                from skillforge.cassette import replay_step_from_cassette
                from skillforge.placeholders import substitute_dict

                # Resolve placeholders to match against cassette (include secrets)
                resolved_step = substitute_dict(step, context, secret_manager)
                result = replay_step_from_cassette(
                    cassette,
                    step_id,
                    resolved_step.get("command", ""),
                    resolved_step.get("cwd", ""),
                )

            # Fall back to actual execution if not replaying or not found
            if result is None:
                result = execute_step(
                    step,
                    context,
                    logs_dir,
                    dry_run,
                    secret_manager=secret_manager,
                    secret_masker=masker,
                )

            step_results[step_id] = result

            # Add to report
            step_data = {
                "id": result.step_id,
                "type": result.step_type,
                "command": result.resolved_command,
                "cwd": result.resolved_cwd,
                "exit_code": result.exit_code,
                "duration_ms": result.duration_ms,
                "status": result.status,
                "error_message": result.error_message,
            }
            # Include stdout/stderr for cassette recording
            if result.stdout:
                step_data["stdout"] = result.stdout
            if result.stderr:
                step_data["stderr"] = result.stderr

            report.steps.append(step_data)

            # Stop on failure (unless dry_run)
            if result.status == "failed" and not dry_run:
                report.failed_step_id = step_id
                report.success = False
                report.error_message = f"Step '{step_id}' failed: {result.error_message}"
                break

        # Execute checks (only if all steps succeeded or dry_run)
        if report.failed_step_id is None or dry_run:
            checks = skill_data.get("checks", [])

            for check in checks:
                check_result = execute_check(check, context, step_results)

                report.checks.append({
                    "id": check_result.check_id,
                    "type": check_result.check_type,
                    "status": check_result.status,
                    "message": check_result.message,
                })

                # Track failures
                if check_result.status == "failed" and not dry_run:
                    if report.error_message:
                        report.error_message += f"; Check '{check_result.check_id}' failed"
                    else:
                        report.error_message = f"Check '{check_result.check_id}' failed: {check_result.message}"
                    report.success = False

            # If no failures, mark as success
            if not report.error_message:
                report.success = True

    except SkillLoadError as e:
        report.error_message = f"Failed to load skill: {e}"
        report.success = False

    except SandboxError as e:
        report.error_message = f"Sandbox error: {e}"
        report.success = False

    except PlaceholderError as e:
        report.error_message = f"Placeholder error: {e}"
        report.success = False

    except SecretNotFoundError as e:
        report.error_message = f"Secret not found: {e}"
        report.success = False

    except Exception as e:
        report.error_message = f"Unexpected error: {e}"
        report.success = False

    # Finalize report
    report.finished_at = datetime.now().isoformat()

    # Write report to disk
    if not dry_run:
        _write_report(skill_dir, run_id, report)

    return report


def _resolve_inputs(
    skill_data: dict[str, Any],
    target_dir: Path,
    overrides: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Resolve input values with defaults and overrides.

    Args:
        skill_data: Loaded skill.yaml data
        target_dir: Target directory path
        overrides: Optional input value overrides

    Returns:
        Dictionary of resolved input values
    """
    inputs_def = skill_data.get("inputs", [])
    resolved = {}

    for inp in inputs_def:
        name = inp.get("name")
        if not name:
            continue

        # Check for override
        if overrides and name in overrides:
            resolved[name] = overrides[name]
        elif "default" in inp:
            resolved[name] = inp["default"]
        elif name == "target_dir":
            # Special case: target_dir defaults to the target directory
            resolved[name] = str(target_dir)
        elif inp.get("required", True):
            # Required input without default
            raise RunError(f"Required input '{name}' not provided")

    return resolved


def _write_report(skill_dir: Path, run_id: str, report: RunReport) -> None:
    """Write run report to disk.

    Args:
        skill_dir: Path to the skill directory
        run_id: Run identifier
        report: Run report to write
    """
    reports_dir = get_reports_path(skill_dir, run_id)
    reports_dir.mkdir(parents=True, exist_ok=True)

    report_file = reports_dir / "run_report.json"
    with open(report_file, "w") as f:
        json.dump(report.to_dict(), f, indent=2)


def get_run_summary(report: RunReport) -> dict[str, Any]:
    """Get a summary of a run report.

    Args:
        report: Run report

    Returns:
        Summary dictionary
    """
    steps_passed = sum(1 for s in report.steps if s["status"] == "success")
    steps_failed = sum(1 for s in report.steps if s["status"] == "failed")
    steps_skipped = sum(1 for s in report.steps if s["status"] == "skipped")

    checks_passed = sum(1 for c in report.checks if c["status"] == "passed")
    checks_failed = sum(1 for c in report.checks if c["status"] == "failed")

    total_duration_ms = sum(s.get("duration_ms", 0) for s in report.steps)

    return {
        "run_id": report.run_id,
        "skill_name": report.skill_name,
        "success": report.success,
        "steps_total": len(report.steps),
        "steps_passed": steps_passed,
        "steps_failed": steps_failed,
        "steps_skipped": steps_skipped,
        "checks_total": len(report.checks),
        "checks_passed": checks_passed,
        "checks_failed": checks_failed,
        "duration_ms": total_duration_ms,
        "error_message": report.error_message,
    }
