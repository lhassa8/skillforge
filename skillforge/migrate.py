"""Migration tools for SkillForge skills.

This module provides tools to migrate skills between SkillForge versions:
- Detect skill format versions
- Upgrade skills to latest format
- Backup and restore during migration
- Batch migration for multiple skills
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

import yaml

from skillforge.skill import Skill, SkillParseError


class SkillFormat(Enum):
    """Skill format versions."""

    UNKNOWN = "unknown"
    V0_1 = "0.1"  # Original format (name, description only)
    V0_9 = "0.9"  # Added version field
    V1_0 = "1.0"  # Current format with all features


class MigrationError(Exception):
    """Raised when migration fails."""

    pass


@dataclass
class MigrationResult:
    """Result of a skill migration.

    Attributes:
        skill_name: Name of the migrated skill
        source_path: Original skill path
        target_path: Migrated skill path
        source_format: Original format version
        target_format: New format version
        changes: List of changes made
        backup_path: Path to backup if created
        success: Whether migration succeeded
        error: Error message if failed
    """

    skill_name: str
    source_path: Path
    target_path: Path
    source_format: SkillFormat
    target_format: SkillFormat
    changes: list[str] = field(default_factory=list)
    backup_path: Optional[Path] = None
    success: bool = True
    error: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "skill_name": self.skill_name,
            "source_path": str(self.source_path),
            "target_path": str(self.target_path),
            "source_format": self.source_format.value,
            "target_format": self.target_format.value,
            "changes": self.changes,
            "backup_path": str(self.backup_path) if self.backup_path else None,
            "success": self.success,
            "error": self.error,
        }


@dataclass
class BatchMigrationResult:
    """Result of a batch migration.

    Attributes:
        total: Total skills processed
        successful: Number of successful migrations
        failed: Number of failed migrations
        skipped: Number of skipped (already current) skills
        results: Individual migration results
    """

    total: int = 0
    successful: int = 0
    failed: int = 0
    skipped: int = 0
    results: list[MigrationResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "total": self.total,
            "successful": self.successful,
            "failed": self.failed,
            "skipped": self.skipped,
            "results": [r.to_dict() for r in self.results],
        }


# =============================================================================
# Format Detection
# =============================================================================


def detect_format(skill_path: Path) -> SkillFormat:
    """Detect the format version of a skill.

    Args:
        skill_path: Path to skill directory

    Returns:
        Detected SkillFormat
    """
    skill_md = skill_path / "SKILL.md"

    if not skill_md.exists():
        return SkillFormat.UNKNOWN

    try:
        content = skill_md.read_text()
    except OSError:
        return SkillFormat.UNKNOWN

    # Parse frontmatter
    frontmatter_match = re.match(
        r"^---\s*\n(.*?)\n---\s*\n",
        content,
        re.DOTALL,
    )

    if not frontmatter_match:
        return SkillFormat.UNKNOWN

    try:
        frontmatter = yaml.safe_load(frontmatter_match.group(1)) or {}
    except yaml.YAMLError:
        return SkillFormat.UNKNOWN

    # Check for format indicators
    has_name = "name" in frontmatter
    has_description = "description" in frontmatter
    has_version = "version" in frontmatter

    # Determine format
    if not has_name or not has_description:
        return SkillFormat.UNKNOWN

    # Check for v1.0 indicators (has schema_version or format_version)
    if frontmatter.get("schema_version") == "1.0" or frontmatter.get("format_version") == "1.0":
        return SkillFormat.V1_0

    # Check for v0.9 indicators (has version field)
    if has_version:
        return SkillFormat.V0_9

    # Basic format with just name/description
    return SkillFormat.V0_1


def get_format_info(format: SkillFormat) -> dict:
    """Get information about a skill format.

    Args:
        format: Skill format version

    Returns:
        Dictionary with format information
    """
    info = {
        SkillFormat.UNKNOWN: {
            "name": "Unknown",
            "description": "Unknown or invalid skill format",
            "features": [],
        },
        SkillFormat.V0_1: {
            "name": "v0.1 (Legacy)",
            "description": "Original skill format with basic metadata",
            "features": ["name", "description", "content"],
        },
        SkillFormat.V0_9: {
            "name": "v0.9 (Versioned)",
            "description": "Added semantic versioning support",
            "features": ["name", "description", "content", "version", "includes"],
        },
        SkillFormat.V1_0: {
            "name": "v1.0 (Current)",
            "description": "Production-ready format with full metadata",
            "features": [
                "name",
                "description",
                "content",
                "version",
                "includes",
                "schema_version",
                "min_skillforge_version",
            ],
        },
    }
    return info.get(format, info[SkillFormat.UNKNOWN])


# =============================================================================
# Migration Functions
# =============================================================================


def create_backup(skill_path: Path, backup_dir: Optional[Path] = None) -> Path:
    """Create a backup of a skill directory.

    Args:
        skill_path: Path to skill to backup
        backup_dir: Directory for backups (default: skill_path.parent/.skillforge-backups)

    Returns:
        Path to backup directory
    """
    if backup_dir is None:
        backup_dir = skill_path.parent / ".skillforge-backups"

    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{skill_path.name}_{timestamp}"
    backup_path = backup_dir / backup_name

    shutil.copytree(skill_path, backup_path)

    return backup_path


def migrate_v01_to_v09(skill_path: Path) -> list[str]:
    """Migrate a v0.1 skill to v0.9 format.

    Args:
        skill_path: Path to skill directory

    Returns:
        List of changes made
    """
    changes = []
    skill_md = skill_path / "SKILL.md"

    content = skill_md.read_text()

    # Parse existing frontmatter
    frontmatter_match = re.match(
        r"^---\s*\n(.*?)\n---\s*\n(.*)$",
        content,
        re.DOTALL,
    )

    if not frontmatter_match:
        raise MigrationError("Invalid SKILL.md format")

    frontmatter = yaml.safe_load(frontmatter_match.group(1)) or {}
    body = frontmatter_match.group(2)

    # Add version if not present
    if "version" not in frontmatter:
        frontmatter["version"] = "1.0.0"
        changes.append("Added version: 1.0.0")

    # Rewrite SKILL.md
    new_frontmatter = yaml.dump(
        frontmatter,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )

    new_content = f"---\n{new_frontmatter}---\n{body}"
    skill_md.write_text(new_content)

    return changes


def migrate_v09_to_v10(skill_path: Path) -> list[str]:
    """Migrate a v0.9 skill to v1.0 format.

    Args:
        skill_path: Path to skill directory

    Returns:
        List of changes made
    """
    changes = []
    skill_md = skill_path / "SKILL.md"

    content = skill_md.read_text()

    # Parse existing frontmatter
    frontmatter_match = re.match(
        r"^---\s*\n(.*?)\n---\s*\n(.*)$",
        content,
        re.DOTALL,
    )

    if not frontmatter_match:
        raise MigrationError("Invalid SKILL.md format")

    frontmatter = yaml.safe_load(frontmatter_match.group(1)) or {}
    body = frontmatter_match.group(2)

    # Add schema_version
    if "schema_version" not in frontmatter:
        frontmatter["schema_version"] = "1.0"
        changes.append("Added schema_version: 1.0")

    # Add min_skillforge_version
    if "min_skillforge_version" not in frontmatter:
        frontmatter["min_skillforge_version"] = "1.0.0"
        changes.append("Added min_skillforge_version: 1.0.0")

    # Ensure version exists
    if "version" not in frontmatter:
        frontmatter["version"] = "1.0.0"
        changes.append("Added version: 1.0.0")

    # Reorder frontmatter for v1.0 standard order
    ordered_keys = [
        "schema_version",
        "name",
        "description",
        "version",
        "min_skillforge_version",
        "includes",
    ]

    ordered_frontmatter = {}
    for key in ordered_keys:
        if key in frontmatter:
            ordered_frontmatter[key] = frontmatter.pop(key)

    # Add remaining keys
    ordered_frontmatter.update(frontmatter)

    # Rewrite SKILL.md
    new_frontmatter = yaml.dump(
        ordered_frontmatter,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )

    new_content = f"---\n{new_frontmatter}---\n{body}"
    skill_md.write_text(new_content)

    if ordered_frontmatter != frontmatter:
        changes.append("Reordered frontmatter fields")

    return changes


def migrate_skill(
    skill_path: Path,
    target_format: SkillFormat = SkillFormat.V1_0,
    create_backup_flag: bool = True,
    backup_dir: Optional[Path] = None,
) -> MigrationResult:
    """Migrate a skill to a target format.

    Args:
        skill_path: Path to skill directory
        target_format: Target format version
        create_backup_flag: Whether to create backup before migration
        backup_dir: Directory for backups

    Returns:
        MigrationResult with migration details
    """
    skill_path = Path(skill_path).resolve()

    # Detect current format
    current_format = detect_format(skill_path)

    # Get skill name
    try:
        skill = Skill.from_directory(skill_path)
        skill_name = skill.name
    except SkillParseError:
        skill_name = skill_path.name

    # Check if migration needed
    if current_format == target_format:
        return MigrationResult(
            skill_name=skill_name,
            source_path=skill_path,
            target_path=skill_path,
            source_format=current_format,
            target_format=target_format,
            changes=["No migration needed - already at target format"],
            success=True,
        )

    if current_format == SkillFormat.UNKNOWN:
        return MigrationResult(
            skill_name=skill_name,
            source_path=skill_path,
            target_path=skill_path,
            source_format=current_format,
            target_format=target_format,
            success=False,
            error="Cannot migrate: unknown or invalid skill format",
        )

    # Create backup
    backup_path = None
    if create_backup_flag:
        try:
            backup_path = create_backup(skill_path, backup_dir)
        except OSError as e:
            return MigrationResult(
                skill_name=skill_name,
                source_path=skill_path,
                target_path=skill_path,
                source_format=current_format,
                target_format=target_format,
                success=False,
                error=f"Failed to create backup: {e}",
            )

    # Perform migration
    all_changes = []

    try:
        # Migrate through each version
        if current_format == SkillFormat.V0_1:
            changes = migrate_v01_to_v09(skill_path)
            all_changes.extend(changes)
            current_format = SkillFormat.V0_9

        if current_format == SkillFormat.V0_9 and target_format == SkillFormat.V1_0:
            changes = migrate_v09_to_v10(skill_path)
            all_changes.extend(changes)
            current_format = SkillFormat.V1_0

        return MigrationResult(
            skill_name=skill_name,
            source_path=skill_path,
            target_path=skill_path,
            source_format=detect_format(skill_path),  # Re-detect after migration
            target_format=target_format,
            changes=all_changes,
            backup_path=backup_path,
            success=True,
        )

    except Exception as e:
        # Restore from backup on failure
        if backup_path and backup_path.exists():
            shutil.rmtree(skill_path)
            shutil.copytree(backup_path, skill_path)

        return MigrationResult(
            skill_name=skill_name,
            source_path=skill_path,
            target_path=skill_path,
            source_format=current_format,
            target_format=target_format,
            backup_path=backup_path,
            success=False,
            error=str(e),
        )


def migrate_directory(
    directory: Path,
    target_format: SkillFormat = SkillFormat.V1_0,
    create_backup_flag: bool = True,
    backup_dir: Optional[Path] = None,
    recursive: bool = False,
) -> BatchMigrationResult:
    """Migrate all skills in a directory.

    Args:
        directory: Directory containing skills
        target_format: Target format version
        create_backup_flag: Whether to create backups
        backup_dir: Directory for backups
        recursive: Whether to search recursively

    Returns:
        BatchMigrationResult with all migration results
    """
    directory = Path(directory).resolve()
    result = BatchMigrationResult()

    # Find skill directories
    skill_dirs = []

    if recursive:
        for skill_md in directory.rglob("SKILL.md"):
            skill_dirs.append(skill_md.parent)
    else:
        for item in directory.iterdir():
            if item.is_dir() and (item / "SKILL.md").exists():
                skill_dirs.append(item)

    result.total = len(skill_dirs)

    for skill_dir in skill_dirs:
        # Check if migration needed
        current_format = detect_format(skill_dir)

        if current_format == target_format:
            result.skipped += 1
            result.results.append(
                MigrationResult(
                    skill_name=skill_dir.name,
                    source_path=skill_dir,
                    target_path=skill_dir,
                    source_format=current_format,
                    target_format=target_format,
                    changes=["Skipped - already at target format"],
                    success=True,
                )
            )
            continue

        # Migrate
        migration_result = migrate_skill(
            skill_dir,
            target_format=target_format,
            create_backup_flag=create_backup_flag,
            backup_dir=backup_dir,
        )

        result.results.append(migration_result)

        if migration_result.success:
            result.successful += 1
        else:
            result.failed += 1

    return result


# =============================================================================
# Validation After Migration
# =============================================================================


def validate_migration(skill_path: Path) -> list[str]:
    """Validate a skill after migration.

    Args:
        skill_path: Path to migrated skill

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        errors.append("SKILL.md not found")
        return errors

    # Try to parse the skill
    try:
        skill = Skill.from_directory(skill_path)
    except SkillParseError as e:
        errors.append(f"Failed to parse skill: {e}")
        return errors

    # Validate required fields
    if not skill.name:
        errors.append("Missing required field: name")
    if not skill.description:
        errors.append("Missing required field: description")

    # Check format is v1.0
    format = detect_format(skill_path)
    if format != SkillFormat.V1_0:
        errors.append(f"Expected v1.0 format, got {format.value}")

    return errors


# =============================================================================
# Utility Functions
# =============================================================================


def list_migrations_needed(directory: Path, recursive: bool = False) -> list[tuple[Path, SkillFormat]]:
    """List skills that need migration.

    Args:
        directory: Directory to scan
        recursive: Whether to search recursively

    Returns:
        List of (skill_path, current_format) tuples for skills needing migration
    """
    directory = Path(directory).resolve()
    needs_migration = []

    if recursive:
        skill_mds = directory.rglob("SKILL.md")
    else:
        skill_mds = directory.glob("*/SKILL.md")

    for skill_md in skill_mds:
        skill_dir = skill_md.parent
        format = detect_format(skill_dir)

        if format != SkillFormat.V1_0 and format != SkillFormat.UNKNOWN:
            needs_migration.append((skill_dir, format))

    return needs_migration


def get_migration_preview(skill_path: Path) -> dict:
    """Get a preview of what migration would change.

    Args:
        skill_path: Path to skill

    Returns:
        Dictionary with migration preview information
    """
    skill_path = Path(skill_path).resolve()
    current_format = detect_format(skill_path)

    preview = {
        "skill_path": str(skill_path),
        "current_format": current_format.value,
        "target_format": SkillFormat.V1_0.value,
        "needs_migration": current_format != SkillFormat.V1_0,
        "planned_changes": [],
    }

    if current_format == SkillFormat.V0_1:
        preview["planned_changes"].extend([
            "Add version: 1.0.0",
            "Add schema_version: 1.0",
            "Add min_skillforge_version: 1.0.0",
            "Reorder frontmatter fields",
        ])
    elif current_format == SkillFormat.V0_9:
        preview["planned_changes"].extend([
            "Add schema_version: 1.0",
            "Add min_skillforge_version: 1.0.0",
            "Reorder frontmatter fields",
        ])
    elif current_format == SkillFormat.V1_0:
        preview["planned_changes"].append("No changes needed")
    else:
        preview["planned_changes"].append("Cannot migrate: unknown format")

    return preview
