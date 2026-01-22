"""Skill composition for combining multiple skills."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from skillforge.skill import Skill, SkillError


class CompositionError(SkillError):
    """Raised when skill composition fails."""
    pass


class CircularDependencyError(CompositionError):
    """Raised when circular dependencies are detected."""
    pass


@dataclass
class CompositionResult:
    """Result of skill composition."""
    success: bool
    skill: Optional[Skill] = None
    composed_content: str = ""
    included_skills: list[str] = field(default_factory=list)
    error: Optional[str] = None


def compose_skill(
    skill_path: Path,
    output_path: Optional[Path] = None,
) -> CompositionResult:
    """Compose a skill by resolving all includes.

    Args:
        skill_path: Path to the composite skill directory
        output_path: Optional path to write composed skill

    Returns:
        CompositionResult with composed skill
    """
    skill_path = Path(skill_path)
    if not skill_path.is_dir():
        return CompositionResult(
            success=False,
            error=f"Skill directory not found: {skill_path}",
        )

    try:
        skill = Skill.from_directory(skill_path)
    except SkillError as e:
        return CompositionResult(success=False, error=str(e))

    # If no includes, return the skill as-is
    if not skill.includes:
        return CompositionResult(
            success=True,
            skill=skill,
            composed_content=skill.to_skill_md(),
            included_skills=[],
        )

    # Resolve all includes
    try:
        resolved = resolve_includes(skill_path)
    except CompositionError as e:
        return CompositionResult(success=False, error=str(e))

    # Build composed content
    composed_content = _build_composed_content(skill, resolved)
    included_names = [s.name for _, s in resolved]

    # Create composed skill without includes (it's now standalone)
    composed_skill = Skill(
        name=skill.name,
        description=skill.description,
        content=composed_content,
        path=skill_path,
        includes=[],  # Composed skill has no includes
    )

    # Write output if path specified
    if output_path:
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)
        skill_md_path = output_path / "SKILL.md"
        skill_md_path.write_text(composed_skill.to_skill_md())

    return CompositionResult(
        success=True,
        skill=composed_skill,
        composed_content=composed_skill.to_skill_md(),
        included_skills=included_names,
    )


def get_includes(skill_path: Path) -> list[Path]:
    """Get list of included skill paths from a skill.

    Args:
        skill_path: Path to the skill directory

    Returns:
        List of resolved include paths
    """
    skill_path = Path(skill_path)
    try:
        skill = Skill.from_directory(skill_path)
    except SkillError:
        return []

    paths = []
    for include in skill.includes:
        include_path = (skill_path / include).resolve()
        paths.append(include_path)

    return paths


def resolve_includes(
    skill_path: Path,
    seen: Optional[set[Path]] = None,
) -> list[tuple[Path, Skill]]:
    """Recursively resolve all includes.

    Detects circular dependencies.

    Args:
        skill_path: Path to the skill directory
        seen: Set of already seen paths for cycle detection

    Returns:
        List of (path, skill) tuples for all resolved includes

    Raises:
        CircularDependencyError: If circular dependencies are detected
        CompositionError: If an included skill cannot be loaded
    """
    skill_path = Path(skill_path).resolve()

    if seen is None:
        seen = set()

    if skill_path in seen:
        raise CircularDependencyError(
            f"Circular dependency detected involving: {skill_path.name}"
        )

    seen.add(skill_path)

    try:
        skill = Skill.from_directory(skill_path)
    except SkillError as e:
        raise CompositionError(f"Failed to load skill at {skill_path}: {e}")

    resolved: list[tuple[Path, Skill]] = []

    for include in skill.includes:
        include_path = (skill_path / include).resolve()

        if not include_path.is_dir():
            raise CompositionError(
                f"Included skill not found: {include} (resolved to {include_path})"
            )

        # Recursively resolve this include's dependencies first
        sub_resolved = resolve_includes(include_path, seen.copy())
        resolved.extend(sub_resolved)

        # Then add this include
        try:
            included_skill = Skill.from_directory(include_path)
            resolved.append((include_path, included_skill))
        except SkillError as e:
            raise CompositionError(f"Failed to load included skill {include}: {e}")

    return resolved


def validate_composition(skill_path: Path) -> list[str]:
    """Validate a composite skill's includes exist.

    Args:
        skill_path: Path to the skill directory

    Returns:
        List of validation error messages (empty if valid)
    """
    skill_path = Path(skill_path)
    errors = []

    try:
        skill = Skill.from_directory(skill_path)
    except SkillError as e:
        return [str(e)]

    if not skill.includes:
        return []

    # Check each include exists
    for include in skill.includes:
        include_path = (skill_path / include).resolve()
        if not include_path.is_dir():
            errors.append(f"Included skill not found: {include}")
        elif not (include_path / "SKILL.md").exists():
            errors.append(f"Included path is not a skill (no SKILL.md): {include}")

    # Check for circular dependencies
    if not errors:
        try:
            resolve_includes(skill_path)
        except CircularDependencyError as e:
            errors.append(str(e))
        except CompositionError as e:
            errors.append(str(e))

    return errors


def _build_composed_content(skill: Skill, resolved: list[tuple[Path, Skill]]) -> str:
    """Build the composed skill content.

    Args:
        skill: The main skill being composed
        resolved: List of resolved includes

    Returns:
        Composed markdown content (without frontmatter)
    """
    parts = [skill.content]

    # Track seen skills to avoid duplicates
    seen_names: set[str] = set()

    for path, included_skill in resolved:
        # Skip duplicates (can happen with shared dependencies)
        if included_skill.name in seen_names:
            continue
        seen_names.add(included_skill.name)

        parts.append(f"\n\n---\n\n## Included: {included_skill.name}\n\n")
        parts.append(included_skill.content)

    return "".join(parts)


def has_includes(skill_path: Path) -> bool:
    """Check if a skill has any includes.

    Args:
        skill_path: Path to the skill directory

    Returns:
        True if the skill has includes
    """
    skill_path = Path(skill_path)
    try:
        skill = Skill.from_directory(skill_path)
        return bool(skill.includes)
    except SkillError:
        return False
