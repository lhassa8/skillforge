"""Scaffold generator for new skills."""

from pathlib import Path
from typing import Optional

import yaml

from skillforge.models import (
    Skill,
    SkillInput,
    Step,
    Check,
    InputType,
    StepType,
    CheckType,
)


def generate_skill_yaml(name: str, description: str = "") -> str:
    """Generate the skill.yaml content for a new skill."""
    skill = Skill(
        name=name,
        version="0.1.0",
        description=description or f"TODO: Describe what {name} does",
        requirements={
            "commands": ["git"],  # Example requirement
        },
        inputs=[
            SkillInput(
                name="target_dir",
                type=InputType.PATH,
                description="Target directory to run the skill against",
                required=True,
            ),
        ],
        preconditions=[
            "Target directory exists",
            "Target directory is a git repository",
        ],
        steps=[
            Step(
                id="example_step",
                type=StepType.SHELL,
                name="Example step",
                command=f"echo 'Hello from {name}'",
                cwd="{target_dir}",
            ),
        ],
        checks=[
            Check(
                id="check_exit_code",
                type=CheckType.EXIT_CODE,
                step_id="example_step",
                equals=0,
            ),
        ],
    )

    # Custom YAML formatting for readability
    return yaml.dump(
        skill.to_dict(),
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
        width=80,
    )


def generate_skill_txt(name: str, description: str = "") -> str:
    """Generate the SKILL.txt content for a new skill."""
    return f"""SKILL: {name}
{'=' * (7 + len(name))}

DESCRIPTION
-----------
{description or f"TODO: Describe what {name} does"}

PRECONDITIONS
-------------
- Target directory must exist
- Target directory should be a git repository

INPUTS
------
- target_dir: Path to the target directory (required)

STEPS
-----
1. Example step
   - Run: echo 'Hello from {name}'
   - Working directory: target_dir

EXPECTED OUTCOMES
-----------------
- Example step completes successfully (exit code 0)

NOTES
-----
- This is a scaffold. Customize the steps and checks as needed.
- Add more detailed documentation here.
"""


def generate_checks_py(name: str) -> str:
    """Generate the checks.py content for a new skill."""
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
    # Example: Check that a file exists
    # target_dir = Path(context["target_dir"])
    # if (target_dir / "some_file.txt").exists():
    #     return True, "File exists"
    # return False, "File not found"

    # Placeholder - always passes
    return True, "Custom check passed"


# Add more custom check functions as needed
'''


def generate_fixture_yaml() -> str:
    """Generate a fixture.yaml template."""
    return """# Fixture configuration
# Override skill inputs for this fixture

# inputs:
#   target_dir: "."  # Usually left as default
#   some_input: "fixture-specific-value"

# allow_extra_files: false  # Set to true to allow files not in expected/
"""


def generate_gitkeep() -> str:
    """Generate a .gitkeep file content."""
    return ""


def create_skill_scaffold(
    name: str,
    output_dir: Path,
    description: str = "",
    force: bool = False,
) -> Path:
    """Create a complete skill scaffold.

    Args:
        name: Name of the skill
        output_dir: Parent directory for the skill folder
        description: Optional description for the skill
        force: If True, overwrite existing skill folder

    Returns:
        Path to the created skill directory

    Raises:
        FileExistsError: If skill directory already exists and force is False
    """
    # Normalize skill name (replace spaces/special chars with underscores)
    safe_name = "".join(c if c.isalnum() or c == "_" else "_" for c in name)
    safe_name = safe_name.strip("_").lower()

    skill_dir = output_dir / safe_name

    if skill_dir.exists() and not force:
        raise FileExistsError(f"Skill directory already exists: {skill_dir}")

    # Create directory structure
    skill_dir.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    fixtures_dir = skill_dir / "fixtures"
    happy_path_dir = fixtures_dir / "happy_path"
    input_dir = happy_path_dir / "input"
    expected_dir = happy_path_dir / "expected"
    reports_dir = skill_dir / "reports"
    cassettes_dir = skill_dir / "cassettes"

    for d in [input_dir, expected_dir, reports_dir, cassettes_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # Generate and write files
    files = {
        skill_dir / "skill.yaml": generate_skill_yaml(name, description),
        skill_dir / "SKILL.txt": generate_skill_txt(name, description),
        skill_dir / "checks.py": generate_checks_py(name),
        happy_path_dir / "fixture.yaml": generate_fixture_yaml(),
        input_dir / ".gitkeep": generate_gitkeep(),
        expected_dir / ".gitkeep": generate_gitkeep(),
        reports_dir / ".gitkeep": generate_gitkeep(),
        cassettes_dir / ".gitkeep": generate_gitkeep(),
    }

    for file_path, content in files.items():
        file_path.write_text(content)

    return skill_dir


def validate_skill_name(name: str) -> tuple[bool, str]:
    """Validate a skill name.

    Args:
        name: The proposed skill name

    Returns:
        Tuple of (is_valid: bool, error_message: str)
    """
    if not name:
        return False, "Skill name cannot be empty"

    if len(name) > 100:
        return False, "Skill name too long (max 100 characters)"

    # Check for at least one alphanumeric character
    if not any(c.isalnum() for c in name):
        return False, "Skill name must contain at least one alphanumeric character"

    return True, ""
