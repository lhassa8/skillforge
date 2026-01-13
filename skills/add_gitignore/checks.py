"""Custom checks for the add_gitignore skill."""

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
    # Example: Check that a file exists
    # target_dir = Path(context["target_dir"])
    # if (target_dir / "some_file.txt").exists():
    #     return True, "File exists"
    # return False, "File not found"

    # Placeholder - always passes
    return True, "Custom check passed"


# Add more custom check functions as needed
