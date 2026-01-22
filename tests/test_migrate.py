"""Tests for skillforge.migrate module."""

import shutil
from pathlib import Path

import pytest
import yaml

from skillforge.migrate import (
    # Enums
    SkillFormat,
    # Dataclasses
    MigrationResult,
    BatchMigrationResult,
    MigrationError,
    # Functions
    detect_format,
    get_format_info,
    create_backup,
    migrate_v01_to_v09,
    migrate_v09_to_v10,
    migrate_skill,
    migrate_directory,
    validate_migration,
    list_migrations_needed,
    get_migration_preview,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def v01_skill(tmp_path: Path) -> Path:
    """Create a v0.1 format skill."""
    skill_dir = tmp_path / "v01-skill"
    skill_dir.mkdir()

    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("""---
name: legacy-skill
description: A legacy skill without version
---

This is the skill content.
""")
    return skill_dir


@pytest.fixture
def v09_skill(tmp_path: Path) -> Path:
    """Create a v0.9 format skill."""
    skill_dir = tmp_path / "v09-skill"
    skill_dir.mkdir()

    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("""---
name: versioned-skill
description: A versioned skill
version: 1.2.0
---

This is the skill content.
""")
    return skill_dir


@pytest.fixture
def v10_skill(tmp_path: Path) -> Path:
    """Create a v1.0 format skill."""
    skill_dir = tmp_path / "v10-skill"
    skill_dir.mkdir()

    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("""---
schema_version: "1.0"
name: modern-skill
description: A modern skill
version: 2.0.0
min_skillforge_version: 1.0.0
---

This is the skill content.
""")
    return skill_dir


@pytest.fixture
def invalid_skill(tmp_path: Path) -> Path:
    """Create an invalid skill directory."""
    skill_dir = tmp_path / "invalid-skill"
    skill_dir.mkdir()

    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("not valid yaml frontmatter")
    return skill_dir


@pytest.fixture
def skills_directory(v01_skill: Path, v09_skill: Path, v10_skill: Path, tmp_path: Path) -> Path:
    """Create a directory with multiple skills."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()

    # Copy skills to the directory
    shutil.copytree(v01_skill, skills_dir / "v01-skill")
    shutil.copytree(v09_skill, skills_dir / "v09-skill")
    shutil.copytree(v10_skill, skills_dir / "v10-skill")

    return skills_dir


# =============================================================================
# SkillFormat Tests
# =============================================================================


class TestSkillFormat:
    """Tests for SkillFormat enum."""

    def test_format_values(self):
        """Test enum values."""
        assert SkillFormat.UNKNOWN.value == "unknown"
        assert SkillFormat.V0_1.value == "0.1"
        assert SkillFormat.V0_9.value == "0.9"
        assert SkillFormat.V1_0.value == "1.0"


# =============================================================================
# Format Detection Tests
# =============================================================================


class TestDetectFormat:
    """Tests for detect_format function."""

    def test_detect_v01_format(self, v01_skill: Path):
        """Test detecting v0.1 format."""
        format = detect_format(v01_skill)
        assert format == SkillFormat.V0_1

    def test_detect_v09_format(self, v09_skill: Path):
        """Test detecting v0.9 format."""
        format = detect_format(v09_skill)
        assert format == SkillFormat.V0_9

    def test_detect_v10_format(self, v10_skill: Path):
        """Test detecting v1.0 format."""
        format = detect_format(v10_skill)
        assert format == SkillFormat.V1_0

    def test_detect_unknown_format(self, invalid_skill: Path):
        """Test detecting unknown format."""
        format = detect_format(invalid_skill)
        assert format == SkillFormat.UNKNOWN

    def test_detect_missing_skill(self, tmp_path: Path):
        """Test detecting format for non-existent skill."""
        format = detect_format(tmp_path / "missing")
        assert format == SkillFormat.UNKNOWN

    def test_detect_no_skill_md(self, tmp_path: Path):
        """Test detecting format for directory without SKILL.md."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        format = detect_format(empty_dir)
        assert format == SkillFormat.UNKNOWN


class TestGetFormatInfo:
    """Tests for get_format_info function."""

    def test_format_info_v01(self):
        """Test v0.1 format info."""
        info = get_format_info(SkillFormat.V0_1)
        assert "Legacy" in info["name"]
        assert "name" in info["features"]
        assert "version" not in info["features"]

    def test_format_info_v09(self):
        """Test v0.9 format info."""
        info = get_format_info(SkillFormat.V0_9)
        assert "version" in info["features"]

    def test_format_info_v10(self):
        """Test v1.0 format info."""
        info = get_format_info(SkillFormat.V1_0)
        assert "Current" in info["name"]
        assert "schema_version" in info["features"]


# =============================================================================
# Backup Tests
# =============================================================================


class TestCreateBackup:
    """Tests for create_backup function."""

    def test_create_backup(self, v01_skill: Path, tmp_path: Path):
        """Test creating a backup."""
        backup_dir = tmp_path / "backups"
        backup_path = create_backup(v01_skill, backup_dir)

        assert backup_path.exists()
        assert backup_path.parent == backup_dir
        assert (backup_path / "SKILL.md").exists()

    def test_create_backup_default_dir(self, v01_skill: Path):
        """Test backup with default directory."""
        backup_path = create_backup(v01_skill)

        assert backup_path.exists()
        assert backup_path.parent.name == ".skillforge-backups"

        # Clean up
        shutil.rmtree(backup_path.parent)

    def test_backup_preserves_content(self, v01_skill: Path, tmp_path: Path):
        """Test backup preserves file content."""
        original_content = (v01_skill / "SKILL.md").read_text()
        backup_path = create_backup(v01_skill, tmp_path / "backups")

        backup_content = (backup_path / "SKILL.md").read_text()
        assert backup_content == original_content


# =============================================================================
# Migration Function Tests
# =============================================================================


class TestMigrateV01ToV09:
    """Tests for migrate_v01_to_v09 function."""

    def test_adds_version(self, v01_skill: Path):
        """Test that migration adds version field."""
        changes = migrate_v01_to_v09(v01_skill)

        assert any("version" in c.lower() for c in changes)

        # Check file was updated
        content = (v01_skill / "SKILL.md").read_text()
        assert "version:" in content


class TestMigrateV09ToV10:
    """Tests for migrate_v09_to_v10 function."""

    def test_adds_schema_version(self, v09_skill: Path):
        """Test that migration adds schema_version."""
        changes = migrate_v09_to_v10(v09_skill)

        assert any("schema_version" in c.lower() for c in changes)

        # Check file was updated
        content = (v09_skill / "SKILL.md").read_text()
        assert "schema_version:" in content

    def test_adds_min_skillforge_version(self, v09_skill: Path):
        """Test that migration adds min_skillforge_version."""
        changes = migrate_v09_to_v10(v09_skill)

        assert any("min_skillforge_version" in c.lower() for c in changes)

        content = (v09_skill / "SKILL.md").read_text()
        assert "min_skillforge_version:" in content


# =============================================================================
# migrate_skill Tests
# =============================================================================


class TestMigrateSkill:
    """Tests for migrate_skill function."""

    def test_migrate_v01_to_v10(self, v01_skill: Path, tmp_path: Path):
        """Test migrating v0.1 to v1.0."""
        result = migrate_skill(
            v01_skill,
            target_format=SkillFormat.V1_0,
            backup_dir=tmp_path / "backups",
        )

        assert result.success
        assert result.source_format == SkillFormat.V1_0  # Re-detected after migration
        assert result.target_format == SkillFormat.V1_0
        assert len(result.changes) > 0
        assert result.backup_path is not None

    def test_migrate_v09_to_v10(self, v09_skill: Path, tmp_path: Path):
        """Test migrating v0.9 to v1.0."""
        result = migrate_skill(
            v09_skill,
            target_format=SkillFormat.V1_0,
            backup_dir=tmp_path / "backups",
        )

        assert result.success
        assert len(result.changes) > 0

    def test_migrate_already_v10(self, v10_skill: Path):
        """Test migrating already v1.0 skill."""
        result = migrate_skill(v10_skill, target_format=SkillFormat.V1_0)

        assert result.success
        assert "no migration needed" in result.changes[0].lower()

    def test_migrate_unknown_format(self, invalid_skill: Path):
        """Test migrating unknown format fails."""
        result = migrate_skill(invalid_skill)

        assert not result.success
        assert "unknown" in result.error.lower()

    def test_migrate_no_backup(self, v01_skill: Path):
        """Test migration without backup."""
        result = migrate_skill(
            v01_skill,
            create_backup_flag=False,
        )

        assert result.success
        assert result.backup_path is None


# =============================================================================
# migrate_directory Tests
# =============================================================================


class TestMigrateDirectory:
    """Tests for migrate_directory function."""

    def test_migrate_directory(self, skills_directory: Path, tmp_path: Path):
        """Test migrating a directory of skills."""
        result = migrate_directory(
            skills_directory,
            backup_dir=tmp_path / "backups",
        )

        assert result.total == 3
        assert result.successful >= 1  # At least v01 and v09 should migrate
        assert result.skipped >= 1  # v10 should be skipped

    def test_migrate_directory_counts(self, skills_directory: Path, tmp_path: Path):
        """Test migration counts are accurate."""
        result = migrate_directory(
            skills_directory,
            backup_dir=tmp_path / "backups",
        )

        assert result.successful + result.failed + result.skipped == result.total

    def test_migrate_directory_recursive(self, tmp_path: Path, v01_skill: Path):
        """Test recursive directory migration."""
        # Create nested structure
        nested_dir = tmp_path / "skills" / "nested"
        nested_dir.mkdir(parents=True)
        shutil.copytree(v01_skill, nested_dir / "skill")

        result = migrate_directory(
            tmp_path / "skills",
            recursive=True,
            backup_dir=tmp_path / "backups",
        )

        assert result.total == 1
        assert result.successful == 1


# =============================================================================
# Validation Tests
# =============================================================================


class TestValidateMigration:
    """Tests for validate_migration function."""

    def test_validate_v10_skill(self, v10_skill: Path):
        """Test validating a v1.0 skill."""
        errors = validate_migration(v10_skill)
        assert errors == []

    def test_validate_migrated_skill(self, v01_skill: Path, tmp_path: Path):
        """Test validating after migration."""
        migrate_skill(v01_skill, backup_dir=tmp_path / "backups")
        errors = validate_migration(v01_skill)
        assert errors == []

    def test_validate_missing_skill(self, tmp_path: Path):
        """Test validating non-existent skill."""
        errors = validate_migration(tmp_path / "missing")
        assert len(errors) > 0


# =============================================================================
# Utility Function Tests
# =============================================================================


class TestListMigrationsNeeded:
    """Tests for list_migrations_needed function."""

    def test_list_migrations(self, skills_directory: Path):
        """Test listing skills needing migration."""
        needs_migration = list_migrations_needed(skills_directory)

        # Should find v01 and v09 skills
        assert len(needs_migration) == 2

        paths = [str(p) for p, _ in needs_migration]
        assert any("v01-skill" in p for p in paths)
        assert any("v09-skill" in p for p in paths)

    def test_list_migrations_empty(self, v10_skill: Path, tmp_path: Path):
        """Test listing when no migrations needed."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        shutil.copytree(v10_skill, skills_dir / "v10-skill")

        needs_migration = list_migrations_needed(skills_dir)
        assert len(needs_migration) == 0


class TestGetMigrationPreview:
    """Tests for get_migration_preview function."""

    def test_preview_v01_skill(self, v01_skill: Path):
        """Test preview for v0.1 skill."""
        preview = get_migration_preview(v01_skill)

        assert preview["current_format"] == "0.1"
        assert preview["target_format"] == "1.0"
        assert preview["needs_migration"] is True
        assert len(preview["planned_changes"]) > 0

    def test_preview_v10_skill(self, v10_skill: Path):
        """Test preview for v1.0 skill."""
        preview = get_migration_preview(v10_skill)

        assert preview["current_format"] == "1.0"
        assert preview["needs_migration"] is False


# =============================================================================
# MigrationResult Tests
# =============================================================================


class TestMigrationResult:
    """Tests for MigrationResult dataclass."""

    def test_to_dict(self, tmp_path: Path):
        """Test conversion to dictionary."""
        result = MigrationResult(
            skill_name="test-skill",
            source_path=tmp_path / "source",
            target_path=tmp_path / "target",
            source_format=SkillFormat.V0_1,
            target_format=SkillFormat.V1_0,
            changes=["Added version"],
            success=True,
        )

        data = result.to_dict()
        assert data["skill_name"] == "test-skill"
        assert data["source_format"] == "0.1"
        assert data["target_format"] == "1.0"
        assert data["success"] is True


class TestBatchMigrationResult:
    """Tests for BatchMigrationResult dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = BatchMigrationResult(
            total=5,
            successful=3,
            failed=1,
            skipped=1,
        )

        data = result.to_dict()
        assert data["total"] == 5
        assert data["successful"] == 3
        assert data["failed"] == 1
        assert data["skipped"] == 1
