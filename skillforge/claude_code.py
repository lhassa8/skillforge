"""Claude Code integration for SkillForge.

Install, uninstall, and manage skills in Claude Code's skills directories.
"""

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

from skillforge.skill import Skill, SkillParseError
from skillforge.validator import validate_skill_directory


# Claude Code skills directories
USER_SKILLS_DIR = Path.home() / ".claude" / "skills"
PROJECT_SKILLS_DIR = Path(".claude") / "skills"

Scope = Literal["user", "project"]


@dataclass
class InstallResult:
    """Result of a skill installation."""

    skill_name: str
    installed_path: Path
    scope: Scope
    was_update: bool = False


@dataclass
class InstalledSkill:
    """Information about an installed skill."""

    name: str
    description: str
    path: Path
    scope: Scope


def get_skills_dir(scope: Scope = "user") -> Path:
    """Get the Claude Code skills directory for the given scope.

    Args:
        scope: "user" for ~/.claude/skills/, "project" for ./.claude/skills/

    Returns:
        Path to the skills directory
    """
    if scope == "user":
        return USER_SKILLS_DIR
    else:
        return PROJECT_SKILLS_DIR.resolve()


def install_skill(
    skill_dir: Path,
    scope: Scope = "user",
    force: bool = False,
) -> InstallResult:
    """Install a skill to Claude Code.

    Copies the skill directory to the appropriate Claude Code skills location.
    Validates the skill before installation.

    Args:
        skill_dir: Path to the skill directory to install
        scope: "user" or "project"
        force: If True, overwrite existing installation

    Returns:
        InstallResult with installation details

    Raises:
        FileNotFoundError: If skill directory doesn't exist
        ValueError: If skill is invalid
        FileExistsError: If skill already installed and force=False
    """
    skill_dir = Path(skill_dir).resolve()

    if not skill_dir.exists():
        raise FileNotFoundError(f"Skill directory not found: {skill_dir}")

    if not skill_dir.is_dir():
        raise ValueError(f"Not a directory: {skill_dir}")

    # Validate the skill
    validation = validate_skill_directory(skill_dir)
    if not validation.valid:
        errors = "; ".join(e.message for e in validation.errors)
        raise ValueError(f"Invalid skill: {errors}")

    # Get skill info
    try:
        skill = Skill.from_directory(skill_dir)
    except SkillParseError as e:
        raise ValueError(f"Failed to parse skill: {e}")

    # Determine target directory
    skills_dir = get_skills_dir(scope)
    target_dir = skills_dir / skill.name

    # Check if already installed
    was_update = target_dir.exists()
    if was_update and not force:
        raise FileExistsError(
            f"Skill '{skill.name}' already installed at {target_dir}. "
            "Use --force to overwrite."
        )

    # Create parent directory if needed
    skills_dir.mkdir(parents=True, exist_ok=True)

    # Remove existing if force
    if was_update:
        shutil.rmtree(target_dir)

    # Copy skill directory
    shutil.copytree(skill_dir, target_dir)

    return InstallResult(
        skill_name=skill.name,
        installed_path=target_dir,
        scope=scope,
        was_update=was_update,
    )


def uninstall_skill(
    skill_name: str,
    scope: Scope = "user",
) -> Optional[Path]:
    """Uninstall a skill from Claude Code.

    Args:
        skill_name: Name of the skill to uninstall
        scope: "user" or "project"

    Returns:
        Path that was removed, or None if skill wasn't installed
    """
    skills_dir = get_skills_dir(scope)
    skill_path = skills_dir / skill_name

    if not skill_path.exists():
        return None

    shutil.rmtree(skill_path)
    return skill_path


def list_installed_skills(
    scope: Optional[Scope] = None,
) -> list[InstalledSkill]:
    """List installed Claude Code skills.

    Args:
        scope: "user", "project", or None for both

    Returns:
        List of InstalledSkill objects
    """
    skills: list[InstalledSkill] = []

    scopes_to_check: list[Scope] = []
    if scope is None:
        scopes_to_check = ["user", "project"]
    else:
        scopes_to_check = [scope]

    for s in scopes_to_check:
        skills_dir = get_skills_dir(s)

        if not skills_dir.exists():
            continue

        for item in skills_dir.iterdir():
            if not item.is_dir():
                continue

            skill_md = item / "SKILL.md"
            if not skill_md.exists():
                continue

            # Try to parse the skill
            try:
                skill = Skill.from_directory(item)
                skills.append(
                    InstalledSkill(
                        name=skill.name,
                        description=skill.description,
                        path=item,
                        scope=s,
                    )
                )
            except SkillParseError:
                # Include but with placeholder description
                skills.append(
                    InstalledSkill(
                        name=item.name,
                        description="(invalid SKILL.md)",
                        path=item,
                        scope=s,
                    )
                )

    return sorted(skills, key=lambda s: (s.scope, s.name))


def sync_skills(
    source_dir: Path,
    scope: Scope = "user",
    force: bool = False,
) -> tuple[list[InstallResult], list[tuple[str, str]]]:
    """Install all skills from a directory.

    Args:
        source_dir: Directory containing skill subdirectories
        scope: "user" or "project"
        force: If True, overwrite existing installations

    Returns:
        Tuple of (list of successful installs, list of (name, error) for failures)
    """
    source_dir = Path(source_dir).resolve()

    if not source_dir.exists():
        raise FileNotFoundError(f"Source directory not found: {source_dir}")

    installed: list[InstallResult] = []
    errors: list[tuple[str, str]] = []

    for item in source_dir.iterdir():
        if not item.is_dir():
            continue

        # Check if it's a skill (has SKILL.md)
        if not (item / "SKILL.md").exists():
            continue

        try:
            result = install_skill(item, scope=scope, force=force)
            installed.append(result)
        except FileExistsError:
            errors.append((item.name, "already installed (use --force)"))
        except (ValueError, FileNotFoundError) as e:
            errors.append((item.name, str(e)))

    return installed, errors


def is_skill_installed(
    skill_name: str,
    scope: Optional[Scope] = None,
) -> bool:
    """Check if a skill is installed.

    Args:
        skill_name: Name of the skill
        scope: "user", "project", or None to check both

    Returns:
        True if skill is installed in the given scope(s)
    """
    scopes_to_check: list[Scope] = []
    if scope is None:
        scopes_to_check = ["user", "project"]
    else:
        scopes_to_check = [scope]

    for s in scopes_to_check:
        skills_dir = get_skills_dir(s)
        skill_path = skills_dir / skill_name

        if skill_path.exists() and (skill_path / "SKILL.md").exists():
            return True

    return False
