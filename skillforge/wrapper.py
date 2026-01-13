"""Wrap existing scripts as SkillForge skills."""

import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml


@dataclass
class ScriptInfo:
    """Information extracted from a script."""

    path: str
    name: str
    type: str  # bash, python, shell, node, ruby, etc.
    shebang: Optional[str] = None
    description: str = ""
    arguments: list[str] = field(default_factory=list)
    env_vars: list[str] = field(default_factory=list)
    has_help: bool = False
    executable: bool = False


@dataclass
class WrapResult:
    """Result of wrapping a script."""

    success: bool = False
    error_message: str = ""
    skill_dir: str = ""
    script_info: Optional[ScriptInfo] = None


class WrapError(Exception):
    """Raised when script wrapping fails."""

    pass


# Map of script types to their common extensions and interpreters
SCRIPT_TYPES = {
    "bash": {
        "extensions": [".sh", ".bash"],
        "interpreter": "bash",
        "shebang_patterns": [r"#!/.*bash"],
    },
    "shell": {
        "extensions": [".sh"],
        "interpreter": "sh",
        "shebang_patterns": [r"#!/bin/sh\b", r"#!/usr/bin/env\s+sh\b"],
    },
    "python": {
        "extensions": [".py"],
        "interpreter": "python",
        "shebang_patterns": [r"#!/.*python"],
    },
    "node": {
        "extensions": [".js", ".mjs"],
        "interpreter": "node",
        "shebang_patterns": [r"#!/.*node"],
    },
    "ruby": {
        "extensions": [".rb"],
        "interpreter": "ruby",
        "shebang_patterns": [r"#!/.*ruby"],
    },
    "perl": {
        "extensions": [".pl", ".pm"],
        "interpreter": "perl",
        "shebang_patterns": [r"#!/.*perl"],
    },
}


def detect_script_type(script_path: Path) -> str:
    """Detect the type of a script from its extension or shebang.

    Args:
        script_path: Path to the script

    Returns:
        Detected script type (bash, python, node, etc.)
    """
    # Check extension first
    ext = script_path.suffix.lower()
    for script_type, info in SCRIPT_TYPES.items():
        if ext in info["extensions"]:
            return script_type

    # Check shebang
    try:
        with open(script_path) as f:
            first_line = f.readline().strip()
            if first_line.startswith("#!"):
                for script_type, info in SCRIPT_TYPES.items():
                    for pattern in info["shebang_patterns"]:
                        if re.match(pattern, first_line):
                            return script_type
    except Exception:
        pass

    # Default to shell
    return "shell"


def analyze_script(script_path: Path, script_type: Optional[str] = None) -> ScriptInfo:
    """Analyze a script and extract useful information.

    Args:
        script_path: Path to the script
        script_type: Optional script type override

    Returns:
        ScriptInfo with extracted information
    """
    if not script_path.exists():
        raise WrapError(f"Script not found: {script_path}")

    # Detect or use provided type
    detected_type = script_type or detect_script_type(script_path)

    info = ScriptInfo(
        path=str(script_path),
        name=script_path.stem,
        type=detected_type,
        executable=script_path.stat().st_mode & 0o111 != 0,
    )

    # Read script content
    try:
        content = script_path.read_text()
        lines = content.split("\n")
    except Exception as e:
        raise WrapError(f"Failed to read script: {e}")

    # Extract shebang
    if lines and lines[0].startswith("#!"):
        info.shebang = lines[0]

    # Extract description from comments
    info.description = _extract_description(lines, detected_type)

    # Extract referenced environment variables
    info.env_vars = _extract_env_vars(content)

    # Check for help/usage
    info.has_help = _has_help_option(content)

    # Extract argument patterns
    info.arguments = _extract_arguments(content, detected_type)

    return info


def _extract_description(lines: list[str], script_type: str) -> str:
    """Extract description from script comments."""
    description_lines = []
    in_header = False

    for line in lines[:30]:  # Only check first 30 lines
        stripped = line.strip()

        # Skip shebang
        if stripped.startswith("#!"):
            continue

        # Python docstring
        if script_type == "python":
            if stripped.startswith('"""') or stripped.startswith("'''"):
                in_header = True
                content = stripped[3:]
                if content.endswith('"""') or content.endswith("'''"):
                    return content[:-3].strip()
                if content:
                    description_lines.append(content)
                continue
            if in_header:
                if stripped.endswith('"""') or stripped.endswith("'''"):
                    if stripped[:-3]:
                        description_lines.append(stripped[:-3])
                    break
                description_lines.append(stripped)
                continue

        # Shell/bash comments
        if stripped.startswith("#"):
            comment = stripped[1:].strip()
            # Skip common non-description comments
            if comment.lower().startswith(("shellcheck", "set ", "author:", "license:")):
                continue
            if comment and not comment.startswith("-"):
                description_lines.append(comment)
                if len(description_lines) >= 3:
                    break
        elif stripped and not in_header:
            # Stop at first non-comment line
            break

    return " ".join(description_lines[:3])


def _extract_env_vars(content: str) -> list[str]:
    """Extract environment variable references from script."""
    # Match $VAR and ${VAR} patterns
    pattern = r'\$\{?([A-Z][A-Z0-9_]*)\}?'
    matches = re.findall(pattern, content)

    # Filter out common shell variables
    common_vars = {"PATH", "HOME", "USER", "PWD", "SHELL", "TERM", "LANG", "LC_ALL"}
    env_vars = sorted(set(m for m in matches if m not in common_vars))

    return env_vars[:10]  # Limit to 10


def _has_help_option(content: str) -> bool:
    """Check if script has help/usage option."""
    help_patterns = [
        r"--help",
        r"-h\b",
        r"usage:",
        r"Usage:",
        r"print_help",
        r"show_help",
        r"argparse",
        r"getopts",
    ]
    return any(re.search(p, content) for p in help_patterns)


def _extract_arguments(content: str, script_type: str) -> list[str]:
    """Extract command line argument patterns."""
    arguments = []

    if script_type == "python":
        # Look for argparse arguments - capture all flag-style args
        # Matches both '-v' and '--verbose' style arguments
        argparse_pattern = r'add_argument\([^)]*[\'"](-{1,2}[\w-]+)[\'"]'
        arguments.extend(re.findall(argparse_pattern, content))
        # Also capture second argument in calls like add_argument('-v', '--verbose')
        argparse_long_pattern = r'add_argument\([\'"][^"\']+[\'"],\s*[\'"](-{1,2}[\w-]+)[\'"]'
        arguments.extend(re.findall(argparse_long_pattern, content))

    elif script_type in ("bash", "shell"):
        # Look for getopts pattern
        getopts_pattern = r'getopts\s+[\'"]([a-zA-Z:]+)[\'"]'
        match = re.search(getopts_pattern, content)
        if match:
            opts = match.group(1).replace(":", "")
            arguments.extend(f"-{c}" for c in opts)

        # Look for case patterns for long options
        case_pattern = r'--([a-z][\w-]*)\)'
        arguments.extend(f"--{m}" for m in re.findall(case_pattern, content))

    return list(set(arguments))[:10]  # Dedupe and limit


def wrap_script(
    script_path: Path,
    output_dir: Path,
    script_type: Optional[str] = None,
    skill_name: Optional[str] = None,
) -> Path:
    """Wrap a script as a SkillForge skill.

    Args:
        script_path: Path to the script to wrap
        output_dir: Directory to create skill in
        script_type: Optional script type override
        skill_name: Optional custom skill name

    Returns:
        Path to created skill directory
    """
    # Analyze script
    info = analyze_script(script_path, script_type)

    # Determine skill name
    name = skill_name or info.name
    safe_name = _normalize_name(name)

    skill_dir = output_dir / safe_name
    skill_dir.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    scripts_dir = skill_dir / "scripts"
    scripts_dir.mkdir(exist_ok=True)
    (skill_dir / "fixtures" / "happy_path" / "input").mkdir(parents=True, exist_ok=True)
    (skill_dir / "fixtures" / "happy_path" / "expected").mkdir(parents=True, exist_ok=True)
    (skill_dir / "reports").mkdir(parents=True, exist_ok=True)
    (skill_dir / "cassettes").mkdir(parents=True, exist_ok=True)

    # Copy script to skill directory
    script_dest = scripts_dir / script_path.name
    shutil.copy2(script_path, script_dest)

    # Make script executable if it wasn't
    script_dest.chmod(script_dest.stat().st_mode | 0o755)

    # Generate skill.yaml
    skill_data = _generate_skill_data(info, script_path.name)
    skill_yaml = skill_dir / "skill.yaml"
    with open(skill_yaml, "w") as f:
        yaml.dump(skill_data, f, default_flow_style=False, sort_keys=False)

    # Generate SKILL.txt
    skill_txt = skill_dir / "SKILL.txt"
    skill_txt.write_text(_generate_skill_txt(info))

    # Generate checks.py
    checks_py = skill_dir / "checks.py"
    checks_py.write_text(_generate_checks_py(info.name))

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


def _normalize_name(name: str) -> str:
    """Normalize a name for use as directory name."""
    safe_name = "".join(c if c.isalnum() or c == "_" else "_" for c in name)
    safe_name = safe_name.strip("_").lower()
    while "__" in safe_name:
        safe_name = safe_name.replace("__", "_")
    return safe_name or "wrapped_script"


def _generate_skill_data(info: ScriptInfo, script_filename: str) -> dict[str, Any]:
    """Generate skill.yaml data from script info."""
    # Get interpreter
    type_info = SCRIPT_TYPES.get(info.type, {})
    interpreter = type_info.get("interpreter", info.type)

    data: dict[str, Any] = {
        "name": _normalize_name(info.name),
        "version": "0.1.0",
        "description": info.description or f"Wrapped {info.type} script: {info.name}",
    }

    # Add metadata
    data["metadata"] = {
        "wrapped_from": info.path,
        "script_type": info.type,
    }

    # Requirements
    data["requirements"] = {
        "commands": [interpreter],
    }

    # Inputs
    data["inputs"] = [
        {
            "name": "target_dir",
            "type": "path",
            "description": "Target directory to run the script against",
            "required": True,
        },
    ]

    # Add arguments input if script takes args
    if info.arguments or info.has_help:
        data["inputs"].append({
            "name": "script_args",
            "type": "string",
            "description": "Additional arguments to pass to the script",
            "required": False,
            "default": "",
        })

    # Note about environment variables
    if info.env_vars:
        data["inputs"].append({
            "name": "env_config",
            "type": "string",
            "description": f"Script may use these env vars: {', '.join(info.env_vars[:5])}",
            "required": False,
            "default": "",
        })

    # Steps
    script_path = f"{{skill_dir}}/scripts/{script_filename}"

    if info.type == "python":
        command = f"python {script_path}"
    elif info.type == "node":
        command = f"node {script_path}"
    elif info.type == "ruby":
        command = f"ruby {script_path}"
    elif info.type == "perl":
        command = f"perl {script_path}"
    else:
        # Bash/shell - run directly if executable, otherwise use interpreter
        command = f"bash {script_path}"

    # Add args placeholder if applicable
    if info.arguments or info.has_help:
        command += " {script_args}"

    data["steps"] = [
        {
            "id": "run_script",
            "type": "shell",
            "name": f"Run {info.name}",
            "command": command,
            "cwd": "{sandbox_dir}",
        },
    ]

    # Checks
    data["checks"] = [
        {
            "id": "check_exit_code",
            "type": "exit_code",
            "step_id": "run_script",
            "equals": 0,
        },
    ]

    return data


def _generate_skill_txt(info: ScriptInfo) -> str:
    """Generate SKILL.txt content."""
    lines = [
        f"SKILL: {_normalize_name(info.name)}",
        "=" * (7 + len(_normalize_name(info.name))),
        "",
        "DESCRIPTION",
        "-----------",
        info.description or f"Wrapped {info.type} script: {info.name}",
        "",
        "SOURCE",
        "------",
        f"Original script: {info.path}",
        f"Script type: {info.type}",
        "",
        "INPUTS",
        "------",
        "- target_dir: path (required) - Target directory",
    ]

    if info.arguments or info.has_help:
        lines.append("- script_args: string (optional) - Arguments to pass to script")

    lines.extend([
        "",
        "STEPS",
        "-----",
        f"1. Run {info.name}",
        f"   - Execute the wrapped {info.type} script",
        "   - Working directory: sandbox_dir",
        "",
        "CHECKS",
        "------",
        "- Script exits with code 0",
        "",
    ])

    if info.arguments:
        lines.extend([
            "DETECTED ARGUMENTS",
            "------------------",
        ])
        for arg in info.arguments[:10]:
            lines.append(f"- {arg}")
        lines.append("")

    if info.env_vars:
        lines.extend([
            "REFERENCED ENVIRONMENT VARIABLES",
            "--------------------------------",
        ])
        for var in info.env_vars[:10]:
            lines.append(f"- {var}")
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
#   script_args: "--verbose"

# allow_extra_files: false
"""


def wrap_script_command(
    script_path: Path,
    output_dir: Path,
    script_type: Optional[str] = None,
    skill_name: Optional[str] = None,
) -> WrapResult:
    """Wrap a script as a skill (main entry point).

    Args:
        script_path: Path to the script
        output_dir: Directory to create skill in
        script_type: Optional script type override
        skill_name: Optional custom skill name

    Returns:
        WrapResult with outcome details
    """
    result = WrapResult()

    try:
        # Analyze script first
        info = analyze_script(script_path, script_type)
        result.script_info = info

        # Wrap the script
        skill_dir = wrap_script(script_path, output_dir, script_type, skill_name)

        result.success = True
        result.skill_dir = str(skill_dir)

    except WrapError as e:
        result.error_message = str(e)

    except Exception as e:
        result.error_message = f"Unexpected error: {e}"

    return result
