"""Check execution for SkillForge skills."""

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from skillforge.executor import StepResult
from skillforge.placeholders import substitute_dict


@dataclass
class CheckResult:
    """Result of executing a single check."""

    check_id: str
    check_type: str
    status: str  # "passed", "failed"
    message: str = ""


def execute_check(
    check: dict[str, Any],
    context: dict[str, Any],
    step_results: dict[str, StepResult],
) -> CheckResult:
    """Execute a single check.

    Args:
        check: Check definition from skill.yaml
        context: Placeholder context for substitution
        step_results: Results from executed steps (keyed by step_id)

    Returns:
        CheckResult with execution details
    """
    check_id = check.get("id", "unknown")
    check_type = check.get("type", "unknown")

    # Resolve placeholders in check
    resolved_check = substitute_dict(check, context)

    if check_type == "file_exists":
        return _check_file_exists(resolved_check)
    elif check_type == "file_contains":
        return _check_file_contains(resolved_check)
    elif check_type == "git_clean":
        return _check_git_clean(resolved_check)
    elif check_type == "stdout_contains":
        return _check_stdout_contains(resolved_check, step_results)
    elif check_type == "exit_code":
        return _check_exit_code(resolved_check, step_results)
    else:
        return CheckResult(
            check_id=check_id,
            check_type=check_type,
            status="failed",
            message=f"Unknown check type: {check_type}",
        )


def _check_file_exists(check: dict[str, Any]) -> CheckResult:
    """Check that a file exists."""
    check_id = check.get("id", "unknown")
    file_path = check.get("path", "")

    path = Path(file_path)

    if path.exists():
        return CheckResult(
            check_id=check_id,
            check_type="file_exists",
            status="passed",
            message=f"File exists: {file_path}",
        )
    else:
        return CheckResult(
            check_id=check_id,
            check_type="file_exists",
            status="failed",
            message=f"File not found: {file_path}",
        )


def _check_file_contains(check: dict[str, Any]) -> CheckResult:
    """Check that a file contains specific content."""
    check_id = check.get("id", "unknown")
    file_path = check.get("path", "")
    contains = check.get("contains")
    regex = check.get("regex")

    path = Path(file_path)

    if not path.exists():
        return CheckResult(
            check_id=check_id,
            check_type="file_contains",
            status="failed",
            message=f"File not found: {file_path}",
        )

    try:
        content = path.read_text()
    except Exception as e:
        return CheckResult(
            check_id=check_id,
            check_type="file_contains",
            status="failed",
            message=f"Error reading file: {e}",
        )

    if contains:
        if contains in content:
            return CheckResult(
                check_id=check_id,
                check_type="file_contains",
                status="passed",
                message=f"File contains '{contains}'",
            )
        else:
            return CheckResult(
                check_id=check_id,
                check_type="file_contains",
                status="failed",
                message=f"File does not contain '{contains}'",
            )

    if regex:
        if re.search(regex, content):
            return CheckResult(
                check_id=check_id,
                check_type="file_contains",
                status="passed",
                message=f"File matches pattern '{regex}'",
            )
        else:
            return CheckResult(
                check_id=check_id,
                check_type="file_contains",
                status="failed",
                message=f"File does not match pattern '{regex}'",
            )

    return CheckResult(
        check_id=check_id,
        check_type="file_contains",
        status="failed",
        message="No 'contains' or 'regex' specified",
    )


def _check_git_clean(check: dict[str, Any]) -> CheckResult:
    """Check that git status is clean."""
    check_id = check.get("id", "unknown")
    cwd = check.get("cwd", ".")

    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            return CheckResult(
                check_id=check_id,
                check_type="git_clean",
                status="failed",
                message=f"git status failed: {result.stderr}",
            )

        if result.stdout.strip():
            # There are uncommitted changes
            lines = result.stdout.strip().split("\n")
            return CheckResult(
                check_id=check_id,
                check_type="git_clean",
                status="failed",
                message=f"Git status not clean: {len(lines)} file(s) with changes",
            )
        else:
            return CheckResult(
                check_id=check_id,
                check_type="git_clean",
                status="passed",
                message="Git status is clean",
            )

    except subprocess.TimeoutExpired:
        return CheckResult(
            check_id=check_id,
            check_type="git_clean",
            status="failed",
            message="git status timed out",
        )
    except FileNotFoundError:
        return CheckResult(
            check_id=check_id,
            check_type="git_clean",
            status="failed",
            message="git not found",
        )
    except Exception as e:
        return CheckResult(
            check_id=check_id,
            check_type="git_clean",
            status="failed",
            message=f"Error checking git status: {e}",
        )


def _check_stdout_contains(
    check: dict[str, Any],
    step_results: dict[str, StepResult],
) -> CheckResult:
    """Check that a step's stdout contains specific content."""
    check_id = check.get("id", "unknown")
    step_id = check.get("step_id", "")
    contains = check.get("contains")
    regex = check.get("regex")

    if step_id not in step_results:
        return CheckResult(
            check_id=check_id,
            check_type="stdout_contains",
            status="failed",
            message=f"Step not found: {step_id}",
        )

    step_result = step_results[step_id]
    stdout = step_result.stdout

    if contains:
        if contains in stdout:
            return CheckResult(
                check_id=check_id,
                check_type="stdout_contains",
                status="passed",
                message=f"stdout contains '{contains}'",
            )
        else:
            return CheckResult(
                check_id=check_id,
                check_type="stdout_contains",
                status="failed",
                message=f"stdout does not contain '{contains}'",
            )

    if regex:
        if re.search(regex, stdout):
            return CheckResult(
                check_id=check_id,
                check_type="stdout_contains",
                status="passed",
                message=f"stdout matches pattern '{regex}'",
            )
        else:
            return CheckResult(
                check_id=check_id,
                check_type="stdout_contains",
                status="failed",
                message=f"stdout does not match pattern '{regex}'",
            )

    return CheckResult(
        check_id=check_id,
        check_type="stdout_contains",
        status="failed",
        message="No 'contains' or 'regex' specified",
    )


def _check_exit_code(
    check: dict[str, Any],
    step_results: dict[str, StepResult],
) -> CheckResult:
    """Check that a step exited with a specific code."""
    check_id = check.get("id", "unknown")
    step_id = check.get("step_id", "")
    expected = check.get("equals", 0)

    if step_id not in step_results:
        return CheckResult(
            check_id=check_id,
            check_type="exit_code",
            status="failed",
            message=f"Step not found: {step_id}",
        )

    step_result = step_results[step_id]
    actual = step_result.exit_code

    if actual == expected:
        return CheckResult(
            check_id=check_id,
            check_type="exit_code",
            status="passed",
            message=f"Exit code {actual} equals expected {expected}",
        )
    else:
        return CheckResult(
            check_id=check_id,
            check_type="exit_code",
            status="failed",
            message=f"Exit code {actual} does not equal expected {expected}",
        )
