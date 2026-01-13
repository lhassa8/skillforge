"""Generate skills from structured spec files."""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml


@dataclass
class ParsedInput:
    """A parsed input definition."""

    name: str
    type: str = "string"
    required: bool = True
    default: Optional[Any] = None
    description: str = ""


@dataclass
class ParsedStep:
    """A parsed step definition."""

    id: str
    name: str
    type: str  # shell, python, file.template, file.replace, json.patch, yaml.patch
    command: Optional[str] = None
    cwd: Optional[str] = None
    path: Optional[str] = None
    template: Optional[str] = None
    pattern: Optional[str] = None
    replace_with: Optional[str] = None
    operations: Optional[list[dict]] = None
    env: Optional[dict[str, str]] = None
    timeout_sec: Optional[int] = None


@dataclass
class ParsedCheck:
    """A parsed check definition."""

    id: str
    type: str  # file_exists, file_contains, exit_code, stdout_contains, git_clean
    step_id: Optional[str] = None
    path: Optional[str] = None
    pattern: Optional[str] = None
    equals: Optional[Any] = None


@dataclass
class ParsedSpec:
    """A fully parsed spec file."""

    name: str
    description: str = ""
    version: str = "0.1.0"
    inputs: list[ParsedInput] = field(default_factory=list)
    preconditions: list[str] = field(default_factory=list)
    steps: list[ParsedStep] = field(default_factory=list)
    checks: list[ParsedCheck] = field(default_factory=list)
    requirements: dict[str, list[str]] = field(default_factory=dict)


class SpecParseError(Exception):
    """Raised when spec parsing fails."""

    pass


def parse_spec_file(spec_path: Path) -> ParsedSpec:
    """Parse a spec file into a ParsedSpec.

    Args:
        spec_path: Path to the spec.txt file

    Returns:
        ParsedSpec with all parsed components

    Raises:
        SpecParseError: If parsing fails
    """
    if not spec_path.exists():
        raise SpecParseError(f"Spec file not found: {spec_path}")

    content = spec_path.read_text()
    return parse_spec_content(content)


def parse_spec_content(content: str) -> ParsedSpec:
    """Parse spec content string into a ParsedSpec.

    Args:
        content: The spec file content

    Returns:
        ParsedSpec with all parsed components

    Raises:
        SpecParseError: If parsing fails
    """
    lines = content.split("\n")
    spec = ParsedSpec(name="")

    current_section = None
    current_step = None
    step_count = 0
    check_count = 0
    multiline_buffer = []
    multiline_field = None

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Skip empty lines and comments
        if not stripped or stripped.startswith("#"):
            i += 1
            continue

        # Handle multiline content (indented continuation)
        if multiline_field and line.startswith("    "):
            multiline_buffer.append(line[4:])  # Remove 4-space indent
            i += 1
            continue
        elif multiline_field:
            # End of multiline, process it
            _apply_multiline(current_step, multiline_field, "\n".join(multiline_buffer))
            multiline_field = None
            multiline_buffer = []

        # Section headers
        if stripped.startswith("SKILL:"):
            spec.name = stripped[6:].strip()
            current_section = "header"
        elif stripped.startswith("DESCRIPTION:"):
            spec.description = stripped[12:].strip()
        elif stripped.startswith("VERSION:"):
            spec.version = stripped[8:].strip()
        elif stripped == "INPUTS:" or stripped.startswith("INPUTS"):
            current_section = "inputs"
        elif stripped == "PRECONDITIONS:" or stripped.startswith("PRECONDITIONS"):
            current_section = "preconditions"
        elif stripped == "REQUIREMENTS:" or stripped.startswith("REQUIREMENTS"):
            current_section = "requirements"
        elif stripped == "STEPS:" or stripped.startswith("STEPS"):
            current_section = "steps"
        elif stripped == "CHECKS:" or stripped.startswith("CHECKS"):
            current_section = "checks"

        # Section content
        elif current_section == "inputs" and stripped.startswith("-"):
            inp = _parse_input_line(stripped[1:].strip())
            if inp:
                spec.inputs.append(inp)

        elif current_section == "preconditions" and stripped.startswith("-"):
            spec.preconditions.append(stripped[1:].strip())

        elif current_section == "requirements" and stripped.startswith("-"):
            req_line = stripped[1:].strip()
            if ":" in req_line:
                key, value = req_line.split(":", 1)
                key = key.strip()
                values = [v.strip() for v in value.split(",")]
                if key not in spec.requirements:
                    spec.requirements[key] = []
                spec.requirements[key].extend(values)

        elif current_section == "steps":
            # Check for step header (numbered line)
            step_match = re.match(r"^(\d+)\.\s*(.+)$", stripped)
            if step_match:
                step_count += 1
                step_name = step_match.group(2)
                step_id = f"step{step_count}"
                current_step = ParsedStep(id=step_id, name=step_name, type="shell")
                spec.steps.append(current_step)
            elif current_step and stripped.startswith("-"):
                # Step property
                prop_line = stripped[1:].strip()
                _parse_step_property(current_step, prop_line)
            elif current_step and ":" in stripped:
                # Direct property (shell:, template:, etc.)
                key, value = stripped.split(":", 1)
                key = key.strip().lower()
                value = value.strip()

                if key == "shell":
                    current_step.type = "shell"
                    current_step.command = value
                elif key == "command":
                    current_step.command = value
                elif key == "cwd":
                    current_step.cwd = value
                elif key == "template":
                    current_step.type = "file.template"
                    current_step.path = value
                elif key == "content":
                    if value == "|":
                        multiline_field = "template"
                        multiline_buffer = []
                    else:
                        current_step.template = value
                elif key == "replace":
                    current_step.type = "file.replace"
                    current_step.path = value
                elif key == "pattern":
                    current_step.pattern = value
                elif key == "with":
                    current_step.replace_with = value
                elif key == "timeout":
                    try:
                        current_step.timeout_sec = int(value)
                    except ValueError:
                        pass

        elif current_section == "checks" and stripped.startswith("-"):
            check_count += 1
            check_line = stripped[1:].strip()
            check = _parse_check_line(check_line, check_count)
            if check:
                spec.checks.append(check)

        i += 1

    # Handle any remaining multiline content
    if multiline_field and multiline_buffer:
        _apply_multiline(current_step, multiline_field, "\n".join(multiline_buffer))

    # Validate
    if not spec.name:
        raise SpecParseError("Spec must have a SKILL: name")

    return spec


def _parse_input_line(line: str) -> Optional[ParsedInput]:
    """Parse an input definition line.

    Format: name: type (required|default: value) - description
    Examples:
        target_dir: path (required) - Target directory
        message: string (default: "hello") - Message to display
        count: integer - Number of items
    """
    # Match: name: type (modifiers) - description
    match = re.match(
        r"^(\w+):\s*(\w+)?\s*(?:\(([^)]+)\))?\s*(?:-\s*(.+))?$",
        line
    )
    if not match:
        # Simple format: just name
        if re.match(r"^\w+$", line):
            return ParsedInput(name=line)
        return None

    name = match.group(1)
    input_type = match.group(2) or "string"
    modifiers = match.group(3) or ""
    description = match.group(4) or ""

    inp = ParsedInput(
        name=name,
        type=input_type.lower(),
        description=description.strip(),
    )

    # Parse modifiers
    if "required" in modifiers.lower():
        inp.required = True
    elif "optional" in modifiers.lower():
        inp.required = False

    # Check for default value
    default_match = re.search(r"default:\s*(.+)", modifiers, re.IGNORECASE)
    if default_match:
        default_val = default_match.group(1).strip()
        # Remove quotes if present
        if default_val.startswith('"') and default_val.endswith('"'):
            default_val = default_val[1:-1]
        elif default_val.startswith("'") and default_val.endswith("'"):
            default_val = default_val[1:-1]
        inp.default = default_val
        inp.required = False

    return inp


def _parse_step_property(step: ParsedStep, line: str) -> None:
    """Parse a step property line."""
    if ":" not in line:
        return

    key, value = line.split(":", 1)
    key = key.strip().lower()
    value = value.strip()

    if key in ("shell", "command"):
        step.type = "shell"
        step.command = value
    elif key == "cwd":
        step.cwd = value
    elif key == "timeout":
        try:
            step.timeout_sec = int(value)
        except ValueError:
            pass


def _parse_check_line(line: str, count: int) -> Optional[ParsedCheck]:
    """Parse a check definition line.

    Formats:
        file_exists: {path}
        file_contains: {path} pattern "regex"
        exit_code: step_id equals 0
        stdout_contains: step_id pattern "text"
        git_clean
    """
    check_id = f"check{count}"

    # file_exists: path
    if line.startswith("file_exists:"):
        path = line[12:].strip()
        return ParsedCheck(id=check_id, type="file_exists", path=path)

    # file_contains: path pattern "regex"
    match = re.match(r"file_contains:\s*(\S+)\s+(?:pattern\s+)?[\"'](.+)[\"']", line)
    if match:
        return ParsedCheck(
            id=check_id,
            type="file_contains",
            path=match.group(1),
            pattern=match.group(2),
        )

    # exit_code: step_id equals N
    match = re.match(r"exit_code:\s*(\w+)\s+equals\s+(\d+)", line)
    if match:
        return ParsedCheck(
            id=check_id,
            type="exit_code",
            step_id=match.group(1),
            equals=int(match.group(2)),
        )

    # stdout_contains: step_id pattern "text"
    match = re.match(r"stdout_contains:\s*(\w+)\s+(?:pattern\s+)?[\"'](.+)[\"']", line)
    if match:
        return ParsedCheck(
            id=check_id,
            type="stdout_contains",
            step_id=match.group(1),
            pattern=match.group(2),
        )

    # git_clean
    if line == "git_clean":
        return ParsedCheck(id=check_id, type="git_clean")

    return None


def _apply_multiline(step: Optional[ParsedStep], field: str, content: str) -> None:
    """Apply multiline content to a step."""
    if not step:
        return

    if field == "template":
        step.template = content


def generate_skill_from_spec(spec: ParsedSpec, output_dir: Path) -> Path:
    """Generate a skill directory from a parsed spec.

    Args:
        spec: Parsed spec
        output_dir: Directory to create skill in

    Returns:
        Path to created skill directory
    """
    # Normalize skill name for directory
    safe_name = "".join(c if c.isalnum() or c == "_" else "_" for c in spec.name)
    safe_name = safe_name.strip("_").lower()

    skill_dir = output_dir / safe_name
    skill_dir.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    (skill_dir / "fixtures" / "happy_path" / "input").mkdir(parents=True, exist_ok=True)
    (skill_dir / "fixtures" / "happy_path" / "expected").mkdir(parents=True, exist_ok=True)
    (skill_dir / "reports").mkdir(parents=True, exist_ok=True)
    (skill_dir / "cassettes").mkdir(parents=True, exist_ok=True)

    # Generate skill.yaml
    skill_data = _spec_to_skill_data(spec)
    skill_yaml = skill_dir / "skill.yaml"
    with open(skill_yaml, "w") as f:
        yaml.dump(skill_data, f, default_flow_style=False, sort_keys=False)

    # Generate SKILL.txt
    skill_txt = skill_dir / "SKILL.txt"
    skill_txt.write_text(_generate_skill_txt(spec))

    # Generate checks.py if needed
    checks_py = skill_dir / "checks.py"
    checks_py.write_text(_generate_checks_py(spec))

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

    return skill_dir


def _spec_to_skill_data(spec: ParsedSpec) -> dict[str, Any]:
    """Convert ParsedSpec to skill.yaml data structure."""
    data: dict[str, Any] = {
        "name": spec.name,
        "version": spec.version,
        "description": spec.description or f"Generated skill: {spec.name}",
    }

    # Requirements
    if spec.requirements:
        data["requirements"] = spec.requirements

    # Inputs
    if spec.inputs:
        data["inputs"] = []
        for inp in spec.inputs:
            inp_data: dict[str, Any] = {
                "name": inp.name,
                "type": inp.type,
            }
            if inp.description:
                inp_data["description"] = inp.description
            if not inp.required:
                inp_data["required"] = False
            if inp.default is not None:
                inp_data["default"] = inp.default
            data["inputs"].append(inp_data)

    # Preconditions
    if spec.preconditions:
        data["preconditions"] = spec.preconditions

    # Steps
    if spec.steps:
        data["steps"] = []
        for step in spec.steps:
            step_data: dict[str, Any] = {
                "id": step.id,
                "type": step.type,
                "name": step.name,
            }

            if step.type == "shell":
                if step.command:
                    step_data["command"] = step.command
                if step.cwd:
                    step_data["cwd"] = step.cwd

            elif step.type == "file.template":
                if step.path:
                    step_data["path"] = step.path
                if step.template:
                    step_data["template"] = step.template

            elif step.type == "file.replace":
                if step.path:
                    step_data["path"] = step.path
                if step.pattern:
                    step_data["pattern"] = step.pattern
                if step.replace_with:
                    step_data["replace_with"] = step.replace_with

            if step.timeout_sec:
                step_data["timeout_sec"] = step.timeout_sec
            if step.env:
                step_data["env"] = step.env

            data["steps"].append(step_data)

    # Checks
    if spec.checks:
        data["checks"] = []
        for check in spec.checks:
            check_data: dict[str, Any] = {
                "id": check.id,
                "type": check.type,
            }

            if check.type == "file_exists":
                check_data["path"] = check.path

            elif check.type == "file_contains":
                check_data["path"] = check.path
                check_data["pattern"] = check.pattern

            elif check.type == "exit_code":
                check_data["step_id"] = check.step_id
                check_data["equals"] = check.equals

            elif check.type == "stdout_contains":
                check_data["step_id"] = check.step_id
                check_data["pattern"] = check.pattern

            elif check.type == "git_clean":
                pass  # No additional fields

            data["checks"].append(check_data)

    return data


def _generate_skill_txt(spec: ParsedSpec) -> str:
    """Generate SKILL.txt content from spec."""
    lines = [
        f"SKILL: {spec.name}",
        "=" * (7 + len(spec.name)),
        "",
        "DESCRIPTION",
        "-----------",
        spec.description or "TODO: Add description",
        "",
    ]

    if spec.preconditions:
        lines.extend([
            "PRECONDITIONS",
            "-------------",
        ])
        for pre in spec.preconditions:
            lines.append(f"- {pre}")
        lines.append("")

    if spec.inputs:
        lines.extend([
            "INPUTS",
            "------",
        ])
        for inp in spec.inputs:
            req = "required" if inp.required else "optional"
            default = f", default: {inp.default}" if inp.default else ""
            desc = f" - {inp.description}" if inp.description else ""
            lines.append(f"- {inp.name}: {inp.type} ({req}{default}){desc}")
        lines.append("")

    if spec.steps:
        lines.extend([
            "STEPS",
            "-----",
        ])
        for i, step in enumerate(spec.steps, 1):
            lines.append(f"{i}. {step.name}")
            if step.type == "shell" and step.command:
                lines.append(f"   - Run: {step.command}")
            elif step.type == "file.template" and step.path:
                lines.append(f"   - Create file: {step.path}")
            elif step.type == "file.replace" and step.path:
                lines.append(f"   - Modify file: {step.path}")
            if step.cwd:
                lines.append(f"   - Working directory: {step.cwd}")
        lines.append("")

    if spec.checks:
        lines.extend([
            "CHECKS",
            "------",
        ])
        for check in spec.checks:
            if check.type == "file_exists":
                lines.append(f"- File exists: {check.path}")
            elif check.type == "file_contains":
                lines.append(f"- File {check.path} contains: {check.pattern}")
            elif check.type == "exit_code":
                lines.append(f"- Step {check.step_id} exits with code {check.equals}")
            elif check.type == "stdout_contains":
                lines.append(f"- Step {check.step_id} output contains: {check.pattern}")
            elif check.type == "git_clean":
                lines.append("- Git working directory is clean")
        lines.append("")

    return "\n".join(lines)


def _generate_checks_py(spec: ParsedSpec) -> str:
    """Generate checks.py content."""
    return f'''"""Custom checks for the {spec.name} skill."""

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
#   some_input: "fixture-specific-value"

# allow_extra_files: false
"""
