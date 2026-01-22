"""Tests for skill lock file management."""

import pytest
import tempfile
from pathlib import Path

from skillforge.lockfile import (
    SkillLockFile,
    LockedSkill,
    LockFileError,
    compute_checksum,
    verify_checksum,
    find_lock_file,
    generate_lock_file,
    verify_against_lock,
    LOCK_FILE_NAME,
)


class TestComputeChecksum:
    """Tests for checksum computation."""

    def test_basic_checksum(self):
        """Test basic checksum computation."""
        content = "Hello, World!"
        checksum = compute_checksum(content)

        assert checksum.startswith("sha256:")
        assert len(checksum) > 10

    def test_consistent_checksum(self):
        """Test checksum is consistent."""
        content = "Test content"
        c1 = compute_checksum(content)
        c2 = compute_checksum(content)

        assert c1 == c2

    def test_different_content_different_checksum(self):
        """Test different content produces different checksum."""
        c1 = compute_checksum("Content A")
        c2 = compute_checksum("Content B")

        assert c1 != c2


class TestVerifyChecksum:
    """Tests for checksum verification."""

    def test_verify_matching_checksum(self):
        """Test verifying matching checksum."""
        content = "Test content"
        checksum = compute_checksum(content)

        assert verify_checksum(content, checksum)

    def test_verify_mismatched_checksum(self):
        """Test verifying mismatched checksum."""
        content = "Test content"
        checksum = compute_checksum(content)

        assert not verify_checksum("Different content", checksum)


class TestLockedSkill:
    """Tests for LockedSkill dataclass."""

    def test_basic_locked_skill(self):
        """Test creating basic locked skill."""
        locked = LockedSkill(
            name="test-skill",
            version="1.0.0",
            source="local:./skills/test",
            checksum="sha256:abc123",
            resolved_at="2026-01-22T10:00:00Z",
        )

        assert locked.name == "test-skill"
        assert locked.version == "1.0.0"

    def test_to_dict(self):
        """Test converting to dictionary."""
        locked = LockedSkill(
            name="test-skill",
            version="1.0.0",
            source="local:./skills/test",
            checksum="sha256:abc123",
            resolved_at="2026-01-22T10:00:00Z",
        )

        d = locked.to_dict()

        assert d["version"] == "1.0.0"
        assert d["source"] == "local:./skills/test"
        assert d["checksum"] == "sha256:abc123"
        assert "name" not in d  # Name is stored as key, not in dict

    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {
            "version": "1.2.3",
            "source": "https://example.com/skills",
            "checksum": "sha256:def456",
            "resolved_at": "2026-01-22T12:00:00Z",
        }

        locked = LockedSkill.from_dict("my-skill", data)

        assert locked.name == "my-skill"
        assert locked.version == "1.2.3"

    def test_verify_checksum_method(self):
        """Test verify_checksum method."""
        content = "SKILL.md content"
        checksum = compute_checksum(content)

        locked = LockedSkill(
            name="test",
            version="1.0.0",
            source="local",
            checksum=checksum,
            resolved_at="",
        )

        assert locked.verify_checksum(content)
        assert not locked.verify_checksum("Different content")


class TestSkillLockFile:
    """Tests for SkillLockFile class."""

    def test_create_empty_lock_file(self):
        """Test creating empty lock file."""
        lock = SkillLockFile()

        assert lock.version == "1"
        assert len(lock.skills) == 0
        assert lock.locked_at != ""

    def test_add_skill(self):
        """Test adding a skill."""
        lock = SkillLockFile()
        content = "Test SKILL.md content"

        locked = lock.add_skill(
            name="test-skill",
            version="1.0.0",
            source="local:./skills/test",
            content=content,
        )

        assert locked.name == "test-skill"
        assert lock.is_locked("test-skill")
        assert len(lock.skills) == 1

    def test_remove_skill(self):
        """Test removing a skill."""
        lock = SkillLockFile()
        lock.add_skill("test", "1.0.0", "local", "content")

        assert lock.is_locked("test")

        removed = lock.remove_skill("test")
        assert removed
        assert not lock.is_locked("test")

    def test_remove_nonexistent_skill(self):
        """Test removing nonexistent skill."""
        lock = SkillLockFile()
        removed = lock.remove_skill("nonexistent")

        assert not removed

    def test_get_skill(self):
        """Test getting a locked skill."""
        lock = SkillLockFile()
        lock.add_skill("test", "1.0.0", "local", "content")

        skill = lock.get_skill("test")
        assert skill is not None
        assert skill.name == "test"

        missing = lock.get_skill("nonexistent")
        assert missing is None

    def test_verify_skill(self):
        """Test verifying a skill."""
        lock = SkillLockFile()
        content = "Test content"
        lock.add_skill("test", "1.0.0", "local", content)

        assert lock.verify_skill("test", content)
        assert not lock.verify_skill("test", "Different content")
        assert not lock.verify_skill("nonexistent", content)

    def test_to_dict(self):
        """Test converting to dictionary."""
        lock = SkillLockFile()
        lock.add_skill("skill-a", "1.0.0", "local", "content a")
        lock.add_skill("skill-b", "2.0.0", "remote", "content b")

        d = lock.to_dict()

        assert d["version"] == "1"
        assert "locked_at" in d
        assert "skills" in d
        assert "skill-a" in d["skills"]
        assert "skill-b" in d["skills"]

    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {
            "version": "1",
            "locked_at": "2026-01-22T10:00:00Z",
            "skills": {
                "test-skill": {
                    "version": "1.2.3",
                    "source": "local",
                    "checksum": "sha256:abc",
                    "resolved_at": "2026-01-22T09:00:00Z",
                }
            }
        }

        lock = SkillLockFile.from_dict(data)

        assert lock.version == "1"
        assert lock.is_locked("test-skill")
        assert lock.skills["test-skill"].version == "1.2.3"

    def test_save_and_load(self):
        """Test saving and loading lock file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir)

            # Create and save
            lock = SkillLockFile()
            lock.add_skill("test", "1.0.0", "local", "content")
            lock.save(lock_path)

            # Verify file exists
            assert (lock_path / LOCK_FILE_NAME).exists()

            # Load and verify
            loaded = SkillLockFile.load(lock_path)
            assert loaded.is_locked("test")
            assert loaded.skills["test"].version == "1.0.0"

    def test_load_nonexistent_raises(self):
        """Test loading nonexistent file raises error."""
        with pytest.raises(LockFileError):
            SkillLockFile.load(Path("/nonexistent/path"))

    def test_load_or_create_creates_new(self):
        """Test load_or_create creates new when not exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir)
            lock = SkillLockFile.load_or_create(lock_path)

            assert lock is not None
            assert len(lock.skills) == 0

    def test_load_or_create_loads_existing(self):
        """Test load_or_create loads existing file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir)

            # Create existing
            original = SkillLockFile()
            original.add_skill("test", "1.0.0", "local", "content")
            original.save(lock_path)

            # Load or create should load existing
            loaded = SkillLockFile.load_or_create(lock_path)
            assert loaded.is_locked("test")


class TestFindLockFile:
    """Tests for find_lock_file function."""

    def test_find_in_current_directory(self):
        """Test finding lock file in current directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            lock_path = root / LOCK_FILE_NAME
            lock_path.write_text("version: '1'\nskills: {}")

            found = find_lock_file(root)
            assert found == lock_path

    def test_find_in_parent_directory(self):
        """Test finding lock file in parent directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            subdir = root / "subdir" / "nested"
            subdir.mkdir(parents=True)

            lock_path = root / LOCK_FILE_NAME
            lock_path.write_text("version: '1'\nskills: {}")

            found = find_lock_file(subdir)
            assert found == lock_path

    def test_find_returns_none_when_not_found(self):
        """Test finding lock file returns None when not found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            found = find_lock_file(Path(tmpdir))
            assert found is None


class TestGenerateLockFile:
    """Tests for generate_lock_file function."""

    def test_generate_from_empty_directory(self):
        """Test generating from empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock = generate_lock_file(Path(tmpdir))
            assert len(lock.skills) == 0

    def test_generate_from_skills_directory(self):
        """Test generating from directory with skills."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir)

            # Create a skill
            skill_dir = skills_dir / "my-skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text("""---
name: my-skill
description: Test skill. Use when testing.
version: 1.2.3
---

Skill content here.
""")

            lock = generate_lock_file(skills_dir)

            assert lock.is_locked("my-skill")
            assert lock.skills["my-skill"].version == "1.2.3"

    def test_generate_skips_invalid_skills(self):
        """Test generating skips invalid skills."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir)

            # Create invalid skill (no SKILL.md)
            (skills_dir / "invalid").mkdir()

            # Create valid skill
            valid_dir = skills_dir / "valid"
            valid_dir.mkdir()
            (valid_dir / "SKILL.md").write_text("""---
name: valid
description: Valid skill. Use when testing.
---

Content.
""")

            lock = generate_lock_file(skills_dir)

            assert lock.is_locked("valid")
            assert not lock.is_locked("invalid")


class TestVerifyAgainstLock:
    """Tests for verify_against_lock function."""

    def test_verify_all_matched(self):
        """Test verification when all skills match."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir)

            # Create skill
            skill_dir = skills_dir / "my-skill"
            skill_dir.mkdir()
            content = """---
name: my-skill
description: Test skill. Use when testing.
---

Content.
"""
            (skill_dir / "SKILL.md").write_text(content)

            # Create lock file
            lock = SkillLockFile()
            lock.add_skill("my-skill", "1.0.0", "local", content)

            result = verify_against_lock(skills_dir, lock)

            assert result.verified
            assert "my-skill" in result.matched
            assert len(result.mismatched) == 0

    def test_verify_detects_mismatch(self):
        """Test verification detects content mismatch."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir)

            # Create skill with original content
            skill_dir = skills_dir / "my-skill"
            skill_dir.mkdir()
            original = """---
name: my-skill
description: Original. Use when testing.
---

Original content.
"""
            (skill_dir / "SKILL.md").write_text(original)

            # Create lock with different content
            lock = SkillLockFile()
            lock.add_skill("my-skill", "1.0.0", "local", "Different content")

            result = verify_against_lock(skills_dir, lock)

            assert not result.verified
            assert "my-skill" in result.mismatched

    def test_verify_detects_missing(self):
        """Test verification detects missing skills."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir)
            skills_dir.mkdir(exist_ok=True)

            # Create lock with skill that doesn't exist
            lock = SkillLockFile()
            lock.add_skill("missing-skill", "1.0.0", "local", "content")

            result = verify_against_lock(skills_dir, lock)

            assert not result.verified
            assert "missing-skill" in result.missing

    def test_verify_detects_unlocked(self):
        """Test verification detects unlocked skills."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir)

            # Create skill that's not in lock file
            skill_dir = skills_dir / "unlocked-skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text("""---
name: unlocked-skill
description: Not locked. Use when testing.
---

Content.
""")

            # Empty lock file
            lock = SkillLockFile()

            result = verify_against_lock(skills_dir, lock)

            # Still verified (unlocked skills are just noted)
            assert result.verified
            assert "unlocked-skill" in result.unlocked
