"""Linter for SkillForge skills - validates structure and checks for issues."""

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from skillforge.loader import load_skill_yaml, get_skill_files, list_fixtures, SkillLoadError


class LintSeverity(Enum):
    """Severity level for lint issues."""

    ERROR = "error"
    WARNING = "warning"


@dataclass
class LintIssue:
    """A single lint issue found in a skill."""

    severity: LintSeverity
    code: str
    message: str
    location: str = ""  # e.g., "steps[0]", "checks[1]"

    def __str__(self) -> str:
        prefix = "ERROR" if self.severity == LintSeverity.ERROR else "WARNING"
        loc = f" ({self.location})" if self.location else ""
        return f"[{prefix}] {self.code}: {self.message}{loc}"


@dataclass
class LintResult:
    """Result of linting a skill."""

    skill_dir: Path
    issues: list[LintIssue] = field(default_factory=list)
    load_error: str | None = None

    @property
    def has_errors(self) -> bool:
        """Check if there are any error-level issues."""
        return self.load_error is not None or any(
            i.severity == LintSeverity.ERROR for i in self.issues
        )

    @property
    def has_warnings(self) -> bool:
        """Check if there are any warning-level issues."""
        return any(i.severity == LintSeverity.WARNING for i in self.issues)

    @property
    def error_count(self) -> int:
        """Count of error-level issues."""
        count = len([i for i in self.issues if i.severity == LintSeverity.ERROR])
        if self.load_error:
            count += 1
        return count

    @property
    def warning_count(self) -> int:
        """Count of warning-level issues."""
        return len([i for i in self.issues if i.severity == LintSeverity.WARNING])


# Patterns that suggest non-deterministic behavior
NON_DETERMINISTIC_PATTERNS = [
    (r"\bdate\b", "date command"),
    (r"\btime\b", "time command"),
    (r"\brandom\b", "random"),
    (r"\buuidgen\b", "uuidgen"),
    (r"\$RANDOM\b", "$RANDOM variable"),
    (r"\bmktemp\b", "mktemp"),
]

# Dangerous patterns
DANGEROUS_PATTERNS = [
    (r"\bsudo\b", "sudo"),
    (r"\brm\s+-rf\b", "rm -rf"),
    (r"\brm\s+-fr\b", "rm -fr"),
]

# Valid placeholder pattern
PLACEHOLDER_PATTERN = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")

# Built-in placeholders
BUILTIN_PLACEHOLDERS = {"target_dir", "sandbox_dir"}


def lint_skill(skill_dir: Path) -> LintResult:
    """Lint a skill directory and return all issues found.

    Args:
        skill_dir: Path to the skill directory

    Returns:
        LintResult containing all issues found
    """
    result = LintResult(skill_dir=skill_dir)

    # Try to load the skill
    try:
        skill_data = load_skill_yaml(skill_dir)
    except SkillLoadError as e:
        result.load_error = str(e)
        return result

    # Run all lint rules
    _check_required_fields(skill_data, result)
    _check_steps(skill_data, result)
    _check_checks(skill_data, result)
    _check_inputs(skill_data, result)
    _check_placeholders(skill_data, result)
    _check_file_structure(skill_dir, result)

    return result


def _check_required_fields(skill_data: dict[str, Any], result: LintResult) -> None:
    """Check for required top-level fields."""
    if "name" not in skill_data:
        result.issues.append(
            LintIssue(
                severity=LintSeverity.ERROR,
                code="E001",
                message="Missing required field: name",
            )
        )

    if "steps" not in skill_data:
        result.issues.append(
            LintIssue(
                severity=LintSeverity.ERROR,
                code="E002",
                message="Missing required field: steps",
            )
        )

    if "inputs" not in skill_data:
        result.issues.append(
            LintIssue(
                severity=LintSeverity.ERROR,
                code="E003",
                message="Missing required field: inputs",
            )
        )


def _check_steps(skill_data: dict[str, Any], result: LintResult) -> None:
    """Check step definitions for issues."""
    steps = skill_data.get("steps", [])

    if not steps:
        result.issues.append(
            LintIssue(
                severity=LintSeverity.ERROR,
                code="E004",
                message="Steps list is empty",
            )
        )
        return

    if not isinstance(steps, list):
        result.issues.append(
            LintIssue(
                severity=LintSeverity.ERROR,
                code="E005",
                message="Steps must be a list",
            )
        )
        return

    # Check for duplicate step IDs
    step_ids: set[str] = set()
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            result.issues.append(
                LintIssue(
                    severity=LintSeverity.ERROR,
                    code="E006",
                    message="Step must be a mapping",
                    location=f"steps[{i}]",
                )
            )
            continue

        step_id = step.get("id")
        if not step_id:
            result.issues.append(
                LintIssue(
                    severity=LintSeverity.ERROR,
                    code="E007",
                    message="Step missing required field: id",
                    location=f"steps[{i}]",
                )
            )
        elif step_id in step_ids:
            result.issues.append(
                LintIssue(
                    severity=LintSeverity.ERROR,
                    code="E008",
                    message=f"Duplicate step id: {step_id}",
                    location=f"steps[{i}]",
                )
            )
        else:
            step_ids.add(step_id)

        # Check for absolute paths
        _check_absolute_paths(step, result, f"steps[{i}]")

        # Check shell commands for issues
        if step.get("type") == "shell":
            command = step.get("command", "")
            _check_shell_command(command, result, f"steps[{i}]")


def _check_checks(skill_data: dict[str, Any], result: LintResult) -> None:
    """Check the checks definitions for issues."""
    steps = skill_data.get("steps", [])
    checks = skill_data.get("checks", [])

    # Get all step IDs
    step_ids = set()
    for step in steps:
        if isinstance(step, dict) and "id" in step:
            step_ids.add(step["id"])

    # Warn if no checks defined
    if steps and not checks:
        result.issues.append(
            LintIssue(
                severity=LintSeverity.WARNING,
                code="W001",
                message="Steps defined but no checks",
            )
        )
        return

    if not isinstance(checks, list):
        return

    # Check for duplicate check IDs and invalid step references
    check_ids: set[str] = set()
    referenced_steps: set[str] = set()

    for i, check in enumerate(checks):
        if not isinstance(check, dict):
            continue

        check_id = check.get("id")
        if check_id:
            if check_id in check_ids:
                result.issues.append(
                    LintIssue(
                        severity=LintSeverity.ERROR,
                        code="E009",
                        message=f"Duplicate check id: {check_id}",
                        location=f"checks[{i}]",
                    )
                )
            else:
                check_ids.add(check_id)

        # Check step_id references
        step_id = check.get("step_id")
        if step_id:
            referenced_steps.add(step_id)
            if step_id not in step_ids:
                result.issues.append(
                    LintIssue(
                        severity=LintSeverity.ERROR,
                        code="E010",
                        message=f"Check references non-existent step: {step_id}",
                        location=f"checks[{i}]",
                    )
                )

        # Check for absolute paths
        _check_absolute_paths(check, result, f"checks[{i}]")

    # Warn about steps without checks
    for step in steps:
        if isinstance(step, dict):
            step_id = step.get("id")
            if step_id and step_id not in referenced_steps:
                result.issues.append(
                    LintIssue(
                        severity=LintSeverity.WARNING,
                        code="W002",
                        message=f"Step has no checks referencing it: {step_id}",
                        location=f"step '{step_id}'",
                    )
                )


def _check_inputs(skill_data: dict[str, Any], result: LintResult) -> None:
    """Check input definitions for issues."""
    inputs = skill_data.get("inputs", [])

    if not isinstance(inputs, list):
        result.issues.append(
            LintIssue(
                severity=LintSeverity.ERROR,
                code="E011",
                message="Inputs must be a list",
            )
        )
        return

    input_names: set[str] = set()
    for i, inp in enumerate(inputs):
        if not isinstance(inp, dict):
            continue

        name = inp.get("name")
        if name:
            if name in input_names:
                result.issues.append(
                    LintIssue(
                        severity=LintSeverity.ERROR,
                        code="E012",
                        message=f"Duplicate input name: {name}",
                        location=f"inputs[{i}]",
                    )
                )
            else:
                input_names.add(name)


def _check_placeholders(skill_data: dict[str, Any], result: LintResult) -> None:
    """Check for invalid placeholder usage."""
    # Collect all valid placeholders
    valid_placeholders = BUILTIN_PLACEHOLDERS.copy()

    inputs = skill_data.get("inputs", [])
    if isinstance(inputs, list):
        for inp in inputs:
            if isinstance(inp, dict) and "name" in inp:
                valid_placeholders.add(inp["name"])

    # Check steps for placeholders
    steps = skill_data.get("steps", [])
    if isinstance(steps, list):
        for i, step in enumerate(steps):
            if isinstance(step, dict):
                _check_placeholders_in_dict(
                    step, valid_placeholders, result, f"steps[{i}]"
                )

    # Check checks for placeholders
    checks = skill_data.get("checks", [])
    if isinstance(checks, list):
        for i, check in enumerate(checks):
            if isinstance(check, dict):
                _check_placeholders_in_dict(
                    check, valid_placeholders, result, f"checks[{i}]"
                )


def _check_placeholders_in_dict(
    data: dict[str, Any],
    valid_placeholders: set[str],
    result: LintResult,
    location: str,
) -> None:
    """Recursively check for invalid placeholders in a dictionary."""
    for key, value in data.items():
        if isinstance(value, str):
            for match in PLACEHOLDER_PATTERN.finditer(value):
                placeholder = match.group(1)
                # Skip 'name' as it's commonly used in templates
                if placeholder not in valid_placeholders and placeholder != "name":
                    result.issues.append(
                        LintIssue(
                            severity=LintSeverity.ERROR,
                            code="E013",
                            message=f"Unknown placeholder: {{{placeholder}}}",
                            location=f"{location}.{key}",
                        )
                    )
        elif isinstance(value, dict):
            _check_placeholders_in_dict(
                value, valid_placeholders, result, f"{location}.{key}"
            )
        elif isinstance(value, list):
            for j, item in enumerate(value):
                if isinstance(item, str):
                    for match in PLACEHOLDER_PATTERN.finditer(item):
                        placeholder = match.group(1)
                        if placeholder not in valid_placeholders and placeholder != "name":
                            result.issues.append(
                                LintIssue(
                                    severity=LintSeverity.ERROR,
                                    code="E013",
                                    message=f"Unknown placeholder: {{{placeholder}}}",
                                    location=f"{location}.{key}[{j}]",
                                )
                            )
                elif isinstance(item, dict):
                    _check_placeholders_in_dict(
                        item, valid_placeholders, result, f"{location}.{key}[{j}]"
                    )


def _check_absolute_paths(
    data: dict[str, Any], result: LintResult, location: str
) -> None:
    """Check for absolute paths in path-like fields."""
    path_fields = ["path", "cwd", "file", "template_file"]

    for field_name in path_fields:
        value = data.get(field_name)
        if isinstance(value, str) and value.startswith("/"):
            # Allow {target_dir} and {sandbox_dir} prefixed paths
            if not value.startswith("{"):
                result.issues.append(
                    LintIssue(
                        severity=LintSeverity.ERROR,
                        code="E014",
                        message=f"Absolute path not allowed: {value}",
                        location=f"{location}.{field_name}",
                    )
                )


def _check_shell_command(command: str, result: LintResult, location: str) -> None:
    """Check a shell command for potential issues."""
    # Check for non-deterministic patterns
    for pattern, name in NON_DETERMINISTIC_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            result.issues.append(
                LintIssue(
                    severity=LintSeverity.WARNING,
                    code="W003",
                    message=f"Potentially non-deterministic: {name}",
                    location=location,
                )
            )

    # Check for dangerous patterns
    for pattern, name in DANGEROUS_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            result.issues.append(
                LintIssue(
                    severity=LintSeverity.WARNING,
                    code="W004",
                    message=f"Potentially dangerous command: {name}",
                    location=location,
                )
            )


def _check_file_structure(skill_dir: Path, result: LintResult) -> None:
    """Check the skill directory structure."""
    files = get_skill_files(skill_dir)
    fixtures = list_fixtures(skill_dir)

    if not files["fixtures/happy_path"]:
        result.issues.append(
            LintIssue(
                severity=LintSeverity.WARNING,
                code="W005",
                message="Missing fixtures/happy_path directory",
            )
        )

    if not fixtures:
        result.issues.append(
            LintIssue(
                severity=LintSeverity.WARNING,
                code="W006",
                message="No fixtures defined",
            )
        )
