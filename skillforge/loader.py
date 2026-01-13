"""Skill loader - loads and parses skill definitions from disk."""

from pathlib import Path
from typing import Any, Optional

import yaml


class SkillLoadError(Exception):
    """Raised when a skill cannot be loaded."""

    pass


def load_skill_yaml(skill_dir: Path) -> dict[str, Any]:
    """Load and parse the skill.yaml file from a skill directory.

    Args:
        skill_dir: Path to the skill directory

    Returns:
        Parsed skill.yaml as a dictionary

    Raises:
        SkillLoadError: If the file cannot be loaded or parsed
    """
    skill_file = skill_dir / "skill.yaml"

    if not skill_dir.exists():
        raise SkillLoadError(f"Skill directory not found: {skill_dir}")

    if not skill_file.exists():
        raise SkillLoadError(f"skill.yaml not found in {skill_dir}")

    try:
        with open(skill_file, "r") as f:
            content = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise SkillLoadError(f"Invalid YAML in skill.yaml: {e}")

    if content is None:
        raise SkillLoadError("skill.yaml is empty")

    if not isinstance(content, dict):
        raise SkillLoadError("skill.yaml must be a YAML mapping")

    return content


def get_skill_files(skill_dir: Path) -> dict[str, bool]:
    """Check which skill files exist.

    Args:
        skill_dir: Path to the skill directory

    Returns:
        Dictionary mapping file/directory names to existence boolean
    """
    return {
        "skill.yaml": (skill_dir / "skill.yaml").exists(),
        "SKILL.txt": (skill_dir / "SKILL.txt").exists(),
        "checks.py": (skill_dir / "checks.py").exists(),
        "fixtures": (skill_dir / "fixtures").is_dir(),
        "fixtures/happy_path": (skill_dir / "fixtures" / "happy_path").is_dir(),
        "cassettes": (skill_dir / "cassettes").is_dir(),
        "reports": (skill_dir / "reports").is_dir(),
    }


def list_fixtures(skill_dir: Path) -> list[str]:
    """List all fixture names in a skill directory.

    Args:
        skill_dir: Path to the skill directory

    Returns:
        List of fixture directory names
    """
    fixtures_dir = skill_dir / "fixtures"
    if not fixtures_dir.is_dir():
        return []

    return [
        d.name
        for d in fixtures_dir.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    ]
