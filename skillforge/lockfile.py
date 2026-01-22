"""Lock file management for reproducible skill installations."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

from skillforge.versioning import SkillVersion, VersionError


class LockFileError(Exception):
    """Raised when lock file operations fail."""
    pass


# Default lock file name
LOCK_FILE_NAME = "skillforge.lock"


@dataclass
class LockedSkill:
    """A locked skill entry with exact version and checksum.

    Attributes:
        name: Skill name
        version: Exact version string
        source: Source URL or path (registry URL or "local:./path")
        checksum: SHA256 checksum of SKILL.md content
        resolved_at: When this version was resolved
    """
    name: str
    version: str
    source: str
    checksum: str
    resolved_at: str  # ISO format datetime

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "version": self.version,
            "source": self.source,
            "checksum": self.checksum,
            "resolved_at": self.resolved_at,
        }

    @classmethod
    def from_dict(cls, name: str, data: dict) -> LockedSkill:
        """Create from dictionary."""
        return cls(
            name=name,
            version=data["version"],
            source=data["source"],
            checksum=data["checksum"],
            resolved_at=data.get("resolved_at", ""),
        )

    def verify_checksum(self, content: str) -> bool:
        """Verify content matches the locked checksum.

        Args:
            content: SKILL.md content to verify

        Returns:
            True if checksum matches
        """
        computed = compute_checksum(content)
        return computed == self.checksum


@dataclass
class SkillLockFile:
    """Lock file for reproducible skill installations.

    The lock file ensures that the exact same versions of skills
    are installed across different environments.

    Format (skillforge.lock):
        version: "1"
        locked_at: "2026-01-22T10:00:00Z"
        skills:
          code-reviewer:
            version: "1.2.0"
            source: "https://github.com/skillforge/community-skills"
            checksum: "sha256:abc123..."
            resolved_at: "2026-01-20T09:00:00Z"
    """
    version: str = "1"
    locked_at: str = ""
    skills: dict[str, LockedSkill] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.locked_at:
            self.locked_at = datetime.now(timezone.utc).isoformat()

    def add_skill(
        self,
        name: str,
        version: str,
        source: str,
        content: str,
    ) -> LockedSkill:
        """Add or update a skill in the lock file.

        Args:
            name: Skill name
            version: Version string
            source: Source URL or path
            content: SKILL.md content for checksum

        Returns:
            The locked skill entry
        """
        checksum = compute_checksum(content)
        locked = LockedSkill(
            name=name,
            version=version,
            source=source,
            checksum=checksum,
            resolved_at=datetime.now(timezone.utc).isoformat(),
        )
        self.skills[name] = locked
        self.locked_at = datetime.now(timezone.utc).isoformat()
        return locked

    def remove_skill(self, name: str) -> bool:
        """Remove a skill from the lock file.

        Args:
            name: Skill name

        Returns:
            True if skill was removed, False if not found
        """
        if name in self.skills:
            del self.skills[name]
            self.locked_at = datetime.now(timezone.utc).isoformat()
            return True
        return False

    def get_skill(self, name: str) -> Optional[LockedSkill]:
        """Get a locked skill by name.

        Args:
            name: Skill name

        Returns:
            LockedSkill if found, None otherwise
        """
        return self.skills.get(name)

    def is_locked(self, name: str) -> bool:
        """Check if a skill is locked.

        Args:
            name: Skill name

        Returns:
            True if skill is in lock file
        """
        return name in self.skills

    def verify_skill(self, name: str, content: str) -> bool:
        """Verify a skill's content matches its locked checksum.

        Args:
            name: Skill name
            content: Current SKILL.md content

        Returns:
            True if checksum matches, False if mismatch or not locked
        """
        locked = self.get_skill(name)
        if not locked:
            return False
        return locked.verify_checksum(content)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "version": self.version,
            "locked_at": self.locked_at,
            "skills": {
                name: locked.to_dict()
                for name, locked in sorted(self.skills.items())
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> SkillLockFile:
        """Create from dictionary."""
        skills = {}
        for name, skill_data in data.get("skills", {}).items():
            skills[name] = LockedSkill.from_dict(name, skill_data)

        return cls(
            version=data.get("version", "1"),
            locked_at=data.get("locked_at", ""),
            skills=skills,
        )

    def save(self, path: Path) -> None:
        """Save lock file to disk.

        Args:
            path: Path to save (file or directory)
        """
        if path.is_dir():
            path = path / LOCK_FILE_NAME

        content = yaml.dump(
            self.to_dict(),
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )
        path.write_text(content)

    @classmethod
    def load(cls, path: Path) -> SkillLockFile:
        """Load lock file from disk.

        Args:
            path: Path to lock file or directory containing it

        Returns:
            SkillLockFile instance

        Raises:
            LockFileError: If lock file doesn't exist or is invalid
        """
        if path.is_dir():
            path = path / LOCK_FILE_NAME

        if not path.exists():
            raise LockFileError(f"Lock file not found: {path}")

        try:
            content = path.read_text()
            data = yaml.safe_load(content)
            if not isinstance(data, dict):
                raise LockFileError(f"Invalid lock file format: {path}")
            return cls.from_dict(data)
        except yaml.YAMLError as e:
            raise LockFileError(f"Invalid YAML in lock file: {e}")

    @classmethod
    def load_or_create(cls, path: Path) -> SkillLockFile:
        """Load existing lock file or create a new one.

        Args:
            path: Path to lock file or directory

        Returns:
            SkillLockFile instance (existing or new)
        """
        try:
            return cls.load(path)
        except LockFileError:
            return cls()


def compute_checksum(content: str) -> str:
    """Compute SHA256 checksum of content.

    Args:
        content: Content to hash

    Returns:
        Checksum string in format "sha256:hexdigest"
    """
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def verify_checksum(content: str, checksum: str) -> bool:
    """Verify content matches a checksum.

    Args:
        content: Content to verify
        checksum: Expected checksum

    Returns:
        True if checksums match
    """
    computed = compute_checksum(content)
    return computed == checksum


def find_lock_file(start_path: Path) -> Optional[Path]:
    """Find lock file by searching up from start path.

    Args:
        start_path: Starting directory

    Returns:
        Path to lock file if found, None otherwise
    """
    current = start_path.resolve()

    while current != current.parent:
        lock_path = current / LOCK_FILE_NAME
        if lock_path.exists():
            return lock_path
        current = current.parent

    return None


def generate_lock_file(
    skills_dir: Path,
    registry_url: Optional[str] = None,
) -> SkillLockFile:
    """Generate a lock file from installed skills.

    Args:
        skills_dir: Directory containing skills
        registry_url: Default registry URL for source

    Returns:
        SkillLockFile with all skills locked
    """
    from skillforge.skill import Skill, SkillParseError

    lock = SkillLockFile()

    if not skills_dir.exists():
        return lock

    for item in skills_dir.iterdir():
        if not item.is_dir():
            continue

        skill_md = item / "SKILL.md"
        if not skill_md.exists():
            continue

        try:
            skill = Skill.from_directory(item)
            content = skill_md.read_text()

            # Determine version
            version = getattr(skill, "version", None) or "0.0.0"
            if isinstance(version, SkillVersion):
                version = str(version)

            # Determine source
            source = f"local:{item}"
            if registry_url:
                source = registry_url

            lock.add_skill(
                name=skill.name,
                version=version,
                source=source,
                content=content,
            )
        except SkillParseError:
            continue

    return lock


@dataclass
class LockVerificationResult:
    """Result of verifying skills against lock file."""
    verified: bool
    matched: list[str] = field(default_factory=list)
    mismatched: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    unlocked: list[str] = field(default_factory=list)


def verify_against_lock(
    skills_dir: Path,
    lock_file: SkillLockFile,
) -> LockVerificationResult:
    """Verify installed skills match the lock file.

    Args:
        skills_dir: Directory containing skills
        lock_file: Lock file to verify against

    Returns:
        Verification result with details
    """
    from skillforge.skill import Skill, SkillParseError

    result = LockVerificationResult(verified=True)

    # Check all locked skills
    for name, locked in lock_file.skills.items():
        skill_dir = skills_dir / name
        skill_md = skill_dir / "SKILL.md"

        if not skill_md.exists():
            result.missing.append(name)
            result.verified = False
            continue

        content = skill_md.read_text()
        if locked.verify_checksum(content):
            result.matched.append(name)
        else:
            result.mismatched.append(name)
            result.verified = False

    # Check for unlocked skills
    if skills_dir.exists():
        for item in skills_dir.iterdir():
            if item.is_dir() and (item / "SKILL.md").exists():
                if item.name not in lock_file.skills:
                    result.unlocked.append(item.name)

    return result
