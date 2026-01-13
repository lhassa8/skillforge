"""Custom checks for the add_readme skill."""

from pathlib import Path
from typing import Any


def check_readme_sections(context: dict[str, Any]) -> tuple[bool, str]:
    """Verify README.md has all expected sections.

    Args:
        context: Dictionary containing:
            - target_dir: Path to the target directory
            - sandbox_dir: Path to the sandbox directory
            - inputs: Resolved input values
            - step_results: Results from executed steps

    Returns:
        Tuple of (success: bool, message: str)
    """
    sandbox_dir = Path(context["sandbox_dir"])
    readme_path = sandbox_dir / "README.md"

    if not readme_path.exists():
        return False, "README.md not found"

    content = readme_path.read_text()

    required_sections = [
        "## Installation",
        "## Usage",
        "## Contributing",
        "## License",
    ]

    missing = []
    for section in required_sections:
        if section not in content:
            missing.append(section)

    if missing:
        return False, f"Missing sections: {', '.join(missing)}"

    return True, "All required sections present"


def check_license_type(context: dict[str, Any]) -> tuple[bool, str]:
    """Verify LICENSE file matches the requested license type.

    Args:
        context: Dictionary containing execution context

    Returns:
        Tuple of (success: bool, message: str)
    """
    sandbox_dir = Path(context["sandbox_dir"])
    license_path = sandbox_dir / "LICENSE"
    inputs = context.get("inputs", {})
    license_type = inputs.get("license", "MIT")

    if not license_path.exists():
        return False, "LICENSE file not found"

    content = license_path.read_text()

    if license_type == "MIT":
        if "MIT License" not in content:
            return False, "LICENSE does not contain MIT License header"
        if "Permission is hereby granted" not in content:
            return False, "LICENSE missing MIT permission text"
    else:
        if f"License: {license_type}" not in content:
            return False, f"LICENSE does not reference {license_type}"

    return True, f"LICENSE correctly set to {license_type}"


def check_gitignore_patterns(context: dict[str, Any]) -> tuple[bool, str]:
    """Verify .gitignore has essential patterns.

    Args:
        context: Dictionary containing execution context

    Returns:
        Tuple of (success: bool, message: str)
    """
    sandbox_dir = Path(context["sandbox_dir"])
    gitignore_path = sandbox_dir / ".gitignore"

    if not gitignore_path.exists():
        return False, ".gitignore not found"

    content = gitignore_path.read_text()

    essential_patterns = [
        "node_modules/",
        ".env",
        "*.log",
    ]

    missing = []
    for pattern in essential_patterns:
        if pattern not in content:
            missing.append(pattern)

    if missing:
        return False, f"Missing patterns: {', '.join(missing)}"

    return True, "All essential .gitignore patterns present"
