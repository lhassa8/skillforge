"""Skill registry for sharing and discovering skills.

This module provides functionality to:
- Publish skills to registries
- Install skills from registries
- Search and discover skills
- Manage skill versions and dependencies
"""

import hashlib
import json
import os
import re
import shutil
import tarfile
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import yaml

from skillforge.config import CONFIG_DIR, load_config, save_config
from skillforge.loader import load_skill_yaml, SkillLoadError


# =============================================================================
# Constants
# =============================================================================

REGISTRY_DIR = CONFIG_DIR / "registry"
INSTALLED_SKILLS_DIR = CONFIG_DIR / "skills"
REGISTRY_CONFIG_FILE = CONFIG_DIR / "registries.yaml"

# Semantic version regex
SEMVER_PATTERN = re.compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)

# Skill name pattern: lowercase, alphanumeric, underscores, hyphens
SKILL_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_-]*$")


# =============================================================================
# Exceptions
# =============================================================================


class RegistryError(Exception):
    """Base exception for registry operations."""
    pass


class SkillNotFoundError(RegistryError):
    """Raised when a skill is not found in any registry."""
    pass


class VersionNotFoundError(RegistryError):
    """Raised when a specific version is not found."""
    pass


class PublishError(RegistryError):
    """Raised when publishing fails."""
    pass


class InstallError(RegistryError):
    """Raised when installation fails."""
    pass


class PackageError(RegistryError):
    """Raised when packaging fails."""
    pass


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class SkillVersion:
    """A specific version of a skill."""

    version: str
    published_at: str
    checksum: str  # SHA256 of the package
    size_bytes: int
    download_url: Optional[str] = None
    changelog: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "version": self.version,
            "published_at": self.published_at,
            "checksum": self.checksum,
            "size_bytes": self.size_bytes,
            "download_url": self.download_url,
            "changelog": self.changelog,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SkillVersion":
        """Create from dictionary."""
        return cls(
            version=data["version"],
            published_at=data["published_at"],
            checksum=data["checksum"],
            size_bytes=data["size_bytes"],
            download_url=data.get("download_url"),
            changelog=data.get("changelog", ""),
        )


@dataclass
class SkillMetadata:
    """Metadata for a skill in the registry."""

    name: str
    description: str
    author: str = ""
    license: str = ""
    homepage: str = ""
    repository: str = ""
    tags: list[str] = field(default_factory=list)
    versions: list[SkillVersion] = field(default_factory=list)
    dependencies: dict[str, str] = field(default_factory=dict)  # name -> version constraint
    created_at: str = ""
    updated_at: str = ""

    @property
    def latest_version(self) -> Optional[str]:
        """Get the latest version string."""
        if not self.versions:
            return None
        # Sort by semantic version, return highest
        sorted_versions = sorted(
            self.versions,
            key=lambda v: parse_version(v.version),
            reverse=True
        )
        return sorted_versions[0].version

    def get_version(self, version: str) -> Optional[SkillVersion]:
        """Get a specific version."""
        for v in self.versions:
            if v.version == version:
                return v
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "author": self.author,
            "license": self.license,
            "homepage": self.homepage,
            "repository": self.repository,
            "tags": self.tags,
            "versions": [v.to_dict() for v in self.versions],
            "dependencies": self.dependencies,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SkillMetadata":
        """Create from dictionary."""
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            author=data.get("author", ""),
            license=data.get("license", ""),
            homepage=data.get("homepage", ""),
            repository=data.get("repository", ""),
            tags=data.get("tags", []),
            versions=[SkillVersion.from_dict(v) for v in data.get("versions", [])],
            dependencies=data.get("dependencies", {}),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )


@dataclass
class RegistryConfig:
    """Configuration for a registry source."""

    name: str
    url: str
    type: str  # "git", "local", "http"
    enabled: bool = True
    priority: int = 0  # Lower = higher priority
    auth_token: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "name": self.name,
            "url": self.url,
            "type": self.type,
            "enabled": self.enabled,
            "priority": self.priority,
        }
        if self.auth_token:
            result["auth_token"] = self.auth_token
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RegistryConfig":
        """Create from dictionary."""
        return cls(
            name=data["name"],
            url=data["url"],
            type=data["type"],
            enabled=data.get("enabled", True),
            priority=data.get("priority", 0),
            auth_token=data.get("auth_token"),
        )


@dataclass
class InstalledSkill:
    """Information about an installed skill."""

    name: str
    version: str
    installed_at: str
    source_registry: str
    path: Path
    checksum: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "installed_at": self.installed_at,
            "source_registry": self.source_registry,
            "path": str(self.path),
            "checksum": self.checksum,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "InstalledSkill":
        """Create from dictionary."""
        return cls(
            name=data["name"],
            version=data["version"],
            installed_at=data["installed_at"],
            source_registry=data["source_registry"],
            path=Path(data["path"]),
            checksum=data["checksum"],
        )


# =============================================================================
# Version Utilities
# =============================================================================


def parse_version(version: str) -> tuple[int, int, int, str, str]:
    """Parse a semantic version string into components.

    Args:
        version: Semantic version string (e.g., "1.2.3-beta+build")

    Returns:
        Tuple of (major, minor, patch, prerelease, buildmetadata)
    """
    match = SEMVER_PATTERN.match(version)
    if not match:
        # Fallback for non-semver strings
        return (0, 0, 0, version, "")

    return (
        int(match.group("major")),
        int(match.group("minor")),
        int(match.group("patch")),
        match.group("prerelease") or "",
        match.group("buildmetadata") or "",
    )


def version_matches(version: str, constraint: str) -> bool:
    """Check if a version matches a constraint.

    Supports:
    - Exact: "1.2.3"
    - Range: ">=1.0.0", "<2.0.0", ">=1.0.0,<2.0.0"
    - Wildcard: "1.2.*", "1.*"
    - Caret: "^1.2.3" (>=1.2.3, <2.0.0)
    - Tilde: "~1.2.3" (>=1.2.3, <1.3.0)

    Args:
        version: Version to check
        constraint: Version constraint

    Returns:
        True if version matches constraint
    """
    if not constraint or constraint == "*":
        return True

    v_parts = parse_version(version)
    v_tuple = v_parts[:3]  # major, minor, patch

    # Handle multiple constraints (comma-separated)
    if "," in constraint:
        constraints = [c.strip() for c in constraint.split(",")]
        return all(version_matches(version, c) for c in constraints)

    # Exact match
    if SEMVER_PATTERN.match(constraint):
        c_parts = parse_version(constraint)
        return v_parts[:3] == c_parts[:3]

    # Wildcard: 1.2.*, 1.*
    if "*" in constraint:
        pattern = constraint.replace(".", r"\.").replace("*", r".*")
        return bool(re.match(f"^{pattern}$", version))

    # Caret: ^1.2.3 means >=1.2.3, <2.0.0
    if constraint.startswith("^"):
        c_version = constraint[1:]
        c_parts = parse_version(c_version)
        c_tuple = c_parts[:3]

        if v_tuple < c_tuple:
            return False
        # Major must be same (for major > 0), or minor must be same (for major = 0)
        if c_tuple[0] > 0:
            return v_tuple[0] == c_tuple[0]
        else:
            return v_tuple[0] == 0 and v_tuple[1] == c_tuple[1]

    # Tilde: ~1.2.3 means >=1.2.3, <1.3.0
    if constraint.startswith("~"):
        c_version = constraint[1:]
        c_parts = parse_version(c_version)
        c_tuple = c_parts[:3]

        if v_tuple < c_tuple:
            return False
        return v_tuple[0] == c_tuple[0] and v_tuple[1] == c_tuple[1]

    # Comparison operators: >=, <=, >, <, =
    for op, cmp_fn in [
        (">=", lambda v, c: v >= c),
        ("<=", lambda v, c: v <= c),
        (">", lambda v, c: v > c),
        ("<", lambda v, c: v < c),
        ("=", lambda v, c: v == c),
    ]:
        if constraint.startswith(op):
            c_version = constraint[len(op):]
            c_parts = parse_version(c_version)
            return cmp_fn(v_tuple, c_parts[:3])

    # Default: exact match
    return version == constraint


def find_best_version(
    versions: list[str],
    constraint: str = "*"
) -> Optional[str]:
    """Find the best (highest) version matching a constraint.

    Args:
        versions: List of available versions
        constraint: Version constraint

    Returns:
        Best matching version, or None if no match
    """
    matching = [v for v in versions if version_matches(v, constraint)]
    if not matching:
        return None

    # Sort by semantic version, return highest
    sorted_versions = sorted(matching, key=parse_version, reverse=True)
    return sorted_versions[0]


# =============================================================================
# Registry Backend Interface
# =============================================================================


class RegistryBackend(ABC):
    """Abstract base class for registry backends."""

    def __init__(self, config: RegistryConfig):
        self.config = config

    @abstractmethod
    def list_skills(self) -> list[SkillMetadata]:
        """List all skills in the registry."""
        pass

    @abstractmethod
    def get_skill(self, name: str) -> Optional[SkillMetadata]:
        """Get metadata for a specific skill."""
        pass

    @abstractmethod
    def search(self, query: str) -> list[SkillMetadata]:
        """Search for skills matching query."""
        pass

    @abstractmethod
    def download(self, name: str, version: str, dest: Path) -> Path:
        """Download a skill package to destination.

        Returns path to downloaded package file.
        """
        pass

    @abstractmethod
    def publish(self, package_path: Path, metadata: SkillMetadata) -> bool:
        """Publish a skill package to the registry."""
        pass

    @abstractmethod
    def sync(self) -> bool:
        """Sync/refresh the registry index."""
        pass


# =============================================================================
# Local Registry Backend
# =============================================================================


class LocalRegistryBackend(RegistryBackend):
    """Local directory-based registry for testing and development."""

    def __init__(self, config: RegistryConfig):
        super().__init__(config)
        self.base_path = Path(config.url)
        self.index_file = self.base_path / "index.json"
        self._index: dict[str, SkillMetadata] = {}
        self._load_index()

    def _load_index(self) -> None:
        """Load the index from disk."""
        if self.index_file.exists():
            try:
                data = json.loads(self.index_file.read_text())
                self._index = {
                    name: SkillMetadata.from_dict(meta)
                    for name, meta in data.get("skills", {}).items()
                }
            except (json.JSONDecodeError, KeyError):
                self._index = {}
        else:
            self._index = {}

    def _save_index(self) -> None:
        """Save the index to disk."""
        self.base_path.mkdir(parents=True, exist_ok=True)
        data = {
            "skills": {name: meta.to_dict() for name, meta in self._index.items()},
            "updated_at": datetime.now().isoformat(),
        }
        self.index_file.write_text(json.dumps(data, indent=2))

    def list_skills(self) -> list[SkillMetadata]:
        """List all skills in the registry."""
        return list(self._index.values())

    def get_skill(self, name: str) -> Optional[SkillMetadata]:
        """Get metadata for a specific skill."""
        return self._index.get(name)

    def search(self, query: str) -> list[SkillMetadata]:
        """Search for skills matching query."""
        query_lower = query.lower()
        results = []
        for meta in self._index.values():
            # Search in name, description, and tags
            if (
                query_lower in meta.name.lower() or
                query_lower in meta.description.lower() or
                any(query_lower in tag.lower() for tag in meta.tags)
            ):
                results.append(meta)
        return results

    def download(self, name: str, version: str, dest: Path) -> Path:
        """Download a skill package to destination."""
        meta = self._index.get(name)
        if not meta:
            raise SkillNotFoundError(f"Skill not found: {name}")

        version_info = meta.get_version(version)
        if not version_info:
            raise VersionNotFoundError(f"Version not found: {name}@{version}")

        # For local registry, packages are stored as name-version.tar.gz
        package_name = f"{name}-{version}.tar.gz"
        package_path = self.base_path / "packages" / package_name

        if not package_path.exists():
            raise RegistryError(f"Package file not found: {package_path}")

        # Copy to destination
        dest.mkdir(parents=True, exist_ok=True)
        dest_path = dest / package_name
        shutil.copy2(package_path, dest_path)

        return dest_path

    def publish(self, package_path: Path, metadata: SkillMetadata) -> bool:
        """Publish a skill package to the registry."""
        # Ensure directories exist
        packages_dir = self.base_path / "packages"
        packages_dir.mkdir(parents=True, exist_ok=True)

        # Get the latest version being published
        if not metadata.versions:
            raise PublishError("No versions in metadata")

        latest = metadata.versions[-1]

        # Copy package
        package_name = f"{metadata.name}-{latest.version}.tar.gz"
        dest_path = packages_dir / package_name
        shutil.copy2(package_path, dest_path)

        # Update index
        if metadata.name in self._index:
            existing = self._index[metadata.name]
            # Add new version if not exists
            existing_versions = {v.version for v in existing.versions}
            if latest.version not in existing_versions:
                existing.versions.append(latest)
                existing.updated_at = datetime.now().isoformat()
        else:
            metadata.created_at = datetime.now().isoformat()
            metadata.updated_at = metadata.created_at
            self._index[metadata.name] = metadata

        self._save_index()
        return True

    def sync(self) -> bool:
        """Sync/refresh the registry index."""
        self._load_index()
        return True


# =============================================================================
# Git Registry Backend
# =============================================================================


class GitRegistryBackend(RegistryBackend):
    """Git-based registry (GitHub, GitLab, etc.)."""

    def __init__(self, config: RegistryConfig):
        super().__init__(config)
        self.cache_dir = REGISTRY_DIR / "cache" / config.name
        self.index_file = self.cache_dir / "index.json"
        self._index: dict[str, SkillMetadata] = {}
        self._ensure_cache()

    def _ensure_cache(self) -> None:
        """Ensure cache directory exists and is up to date."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        if self.index_file.exists():
            self._load_index()

    def _load_index(self) -> None:
        """Load the index from cache."""
        if self.index_file.exists():
            try:
                data = json.loads(self.index_file.read_text())
                self._index = {
                    name: SkillMetadata.from_dict(meta)
                    for name, meta in data.get("skills", {}).items()
                }
            except (json.JSONDecodeError, KeyError):
                self._index = {}

    def _save_index(self) -> None:
        """Save the index to cache."""
        data = {
            "skills": {name: meta.to_dict() for name, meta in self._index.items()},
            "updated_at": datetime.now().isoformat(),
        }
        self.index_file.write_text(json.dumps(data, indent=2))

    def _run_git(self, *args: str, cwd: Optional[Path] = None) -> tuple[bool, str]:
        """Run a git command."""
        import subprocess

        cmd = ["git"] + list(args)
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd or self.cache_dir,
                capture_output=True,
                text=True,
                timeout=60,
            )
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, "Git command timed out"
        except Exception as e:
            return False, str(e)

    def sync(self) -> bool:
        """Sync/refresh the registry by pulling from git."""
        repo_dir = self.cache_dir / "repo"

        if repo_dir.exists():
            # Pull latest
            success, _ = self._run_git("pull", "--ff-only", cwd=repo_dir)
            if not success:
                # Try reset
                self._run_git("fetch", "origin", cwd=repo_dir)
                self._run_git("reset", "--hard", "origin/main", cwd=repo_dir)
        else:
            # Clone
            repo_dir.parent.mkdir(parents=True, exist_ok=True)
            success, output = self._run_git(
                "clone", "--depth", "1", self.config.url, str(repo_dir),
                cwd=repo_dir.parent
            )
            if not success:
                raise RegistryError(f"Failed to clone registry: {output}")

        # Load index from repo
        index_path = repo_dir / "index.json"
        if index_path.exists():
            try:
                data = json.loads(index_path.read_text())
                self._index = {
                    name: SkillMetadata.from_dict(meta)
                    for name, meta in data.get("skills", {}).items()
                }
                self._save_index()  # Cache locally
                return True
            except (json.JSONDecodeError, KeyError) as e:
                raise RegistryError(f"Invalid index format: {e}")

        return False

    def list_skills(self) -> list[SkillMetadata]:
        """List all skills in the registry."""
        return list(self._index.values())

    def get_skill(self, name: str) -> Optional[SkillMetadata]:
        """Get metadata for a specific skill."""
        return self._index.get(name)

    def search(self, query: str) -> list[SkillMetadata]:
        """Search for skills matching query."""
        query_lower = query.lower()
        results = []
        for meta in self._index.values():
            if (
                query_lower in meta.name.lower() or
                query_lower in meta.description.lower() or
                any(query_lower in tag.lower() for tag in meta.tags)
            ):
                results.append(meta)
        return results

    def download(self, name: str, version: str, dest: Path) -> Path:
        """Download a skill package."""
        meta = self._index.get(name)
        if not meta:
            raise SkillNotFoundError(f"Skill not found: {name}")

        version_info = meta.get_version(version)
        if not version_info:
            raise VersionNotFoundError(f"Version not found: {name}@{version}")

        # Check for download URL
        if version_info.download_url:
            return self._download_from_url(version_info.download_url, name, version, dest)

        # Otherwise, look in repo packages directory
        repo_dir = self.cache_dir / "repo"
        package_name = f"{name}-{version}.tar.gz"
        package_path = repo_dir / "packages" / package_name

        if not package_path.exists():
            raise RegistryError(f"Package not found in repository: {package_name}")

        dest.mkdir(parents=True, exist_ok=True)
        dest_path = dest / package_name
        shutil.copy2(package_path, dest_path)

        return dest_path

    def _download_from_url(
        self, url: str, name: str, version: str, dest: Path
    ) -> Path:
        """Download package from URL."""
        try:
            import httpx
        except ImportError:
            raise RegistryError("httpx package required for URL downloads. Run: pip install httpx")

        dest.mkdir(parents=True, exist_ok=True)
        package_name = f"{name}-{version}.tar.gz"
        dest_path = dest / package_name

        try:
            with httpx.stream("GET", url, follow_redirects=True, timeout=60.0) as response:
                response.raise_for_status()
                with open(dest_path, "wb") as f:
                    for chunk in response.iter_bytes():
                        f.write(chunk)
        except Exception as e:
            raise RegistryError(f"Download failed: {e}")

        return dest_path

    def publish(self, package_path: Path, metadata: SkillMetadata) -> bool:
        """Publish to git registry (creates a PR or pushes directly)."""
        # For git registries, publishing typically requires:
        # 1. Fork/clone the registry
        # 2. Add package and update index
        # 3. Create PR or push
        # This is a complex operation that depends on permissions

        raise PublishError(
            "Direct publishing to Git registries requires write access. "
            "Please fork the registry and submit a pull request."
        )


# =============================================================================
# Registry Manager
# =============================================================================


class RegistryManager:
    """Manages multiple registry sources and installed skills."""

    def __init__(self):
        self.registries: list[RegistryBackend] = []
        self._installed: dict[str, InstalledSkill] = {}
        self._load_config()
        self._load_installed()

    def _load_config(self) -> None:
        """Load registry configuration."""
        if not REGISTRY_CONFIG_FILE.exists():
            # Create default config
            self._save_default_config()

        try:
            data = yaml.safe_load(REGISTRY_CONFIG_FILE.read_text()) or {}
            for reg_data in data.get("registries", []):
                config = RegistryConfig.from_dict(reg_data)
                if config.enabled:
                    backend = self._create_backend(config)
                    if backend:
                        self.registries.append(backend)
        except Exception:
            pass

        # Sort by priority
        self.registries.sort(key=lambda r: r.config.priority)

    def _save_default_config(self) -> None:
        """Save default registry configuration."""
        REGISTRY_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        default_config = {
            "registries": [
                {
                    "name": "local",
                    "url": str(REGISTRY_DIR / "local"),
                    "type": "local",
                    "enabled": True,
                    "priority": 100,
                }
            ]
        }
        REGISTRY_CONFIG_FILE.write_text(yaml.dump(default_config, default_flow_style=False))

    def _create_backend(self, config: RegistryConfig) -> Optional[RegistryBackend]:
        """Create a backend for the given config."""
        if config.type == "local":
            return LocalRegistryBackend(config)
        elif config.type == "git":
            return GitRegistryBackend(config)
        return None

    def _load_installed(self) -> None:
        """Load list of installed skills."""
        installed_file = INSTALLED_SKILLS_DIR / "installed.json"
        if installed_file.exists():
            try:
                data = json.loads(installed_file.read_text())
                self._installed = {
                    name: InstalledSkill.from_dict(info)
                    for name, info in data.items()
                }
            except (json.JSONDecodeError, KeyError):
                self._installed = {}

    def _save_installed(self) -> None:
        """Save list of installed skills."""
        INSTALLED_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
        installed_file = INSTALLED_SKILLS_DIR / "installed.json"
        data = {name: info.to_dict() for name, info in self._installed.items()}
        installed_file.write_text(json.dumps(data, indent=2))

    def add_registry(
        self,
        name: str,
        url: str,
        registry_type: str = "git",
        priority: int = 50,
    ) -> RegistryConfig:
        """Add a new registry source."""
        config = RegistryConfig(
            name=name,
            url=url,
            type=registry_type,
            enabled=True,
            priority=priority,
        )

        # Save to config file
        if REGISTRY_CONFIG_FILE.exists():
            data = yaml.safe_load(REGISTRY_CONFIG_FILE.read_text()) or {}
        else:
            data = {"registries": []}

        # Check for duplicate
        for reg in data.get("registries", []):
            if reg.get("name") == name:
                raise RegistryError(f"Registry already exists: {name}")

        data.setdefault("registries", []).append(config.to_dict())
        REGISTRY_CONFIG_FILE.write_text(yaml.dump(data, default_flow_style=False))

        # Add to active registries
        backend = self._create_backend(config)
        if backend:
            self.registries.append(backend)
            self.registries.sort(key=lambda r: r.config.priority)

        return config

    def remove_registry(self, name: str) -> bool:
        """Remove a registry source."""
        if not REGISTRY_CONFIG_FILE.exists():
            return False

        data = yaml.safe_load(REGISTRY_CONFIG_FILE.read_text()) or {}
        registries = data.get("registries", [])

        # Find and remove
        new_registries = [r for r in registries if r.get("name") != name]
        if len(new_registries) == len(registries):
            return False

        data["registries"] = new_registries
        REGISTRY_CONFIG_FILE.write_text(yaml.dump(data, default_flow_style=False))

        # Remove from active
        self.registries = [r for r in self.registries if r.config.name != name]

        return True

    def list_registries(self) -> list[RegistryConfig]:
        """List all configured registries."""
        return [r.config for r in self.registries]

    def sync_all(self) -> dict[str, bool]:
        """Sync all registries."""
        results = {}
        for registry in self.registries:
            try:
                results[registry.config.name] = registry.sync()
            except Exception as e:
                results[registry.config.name] = False
        return results

    def search(self, query: str) -> list[tuple[str, SkillMetadata]]:
        """Search for skills across all registries.

        Returns list of (registry_name, metadata) tuples.
        """
        results = []
        seen = set()

        for registry in self.registries:
            for meta in registry.search(query):
                if meta.name not in seen:
                    results.append((registry.config.name, meta))
                    seen.add(meta.name)

        return results

    def get_skill(self, name: str) -> Optional[tuple[str, SkillMetadata]]:
        """Get skill metadata from the first registry that has it.

        Returns (registry_name, metadata) or None.
        """
        for registry in self.registries:
            meta = registry.get_skill(name)
            if meta:
                return (registry.config.name, meta)
        return None

    def install(
        self,
        name: str,
        version: Optional[str] = None,
        force: bool = False,
    ) -> InstalledSkill:
        """Install a skill from registry.

        Args:
            name: Skill name
            version: Version constraint (default: latest)
            force: Reinstall if already installed

        Returns:
            InstalledSkill info
        """
        # Check if already installed
        if name in self._installed and not force:
            existing = self._installed[name]
            if version is None or version_matches(existing.version, version):
                raise InstallError(
                    f"Skill already installed: {name}@{existing.version}. "
                    "Use --force to reinstall."
                )

        # Find skill in registries
        result = self.get_skill(name)
        if not result:
            raise SkillNotFoundError(f"Skill not found: {name}")

        registry_name, metadata = result

        # Resolve version
        available_versions = [v.version for v in metadata.versions]
        if not available_versions:
            raise VersionNotFoundError(f"No versions available for: {name}")

        target_version = find_best_version(
            available_versions,
            version or "*"
        )
        if not target_version:
            raise VersionNotFoundError(
                f"No version matching '{version}' found for: {name}"
            )

        # Find registry backend
        registry = next(
            (r for r in self.registries if r.config.name == registry_name),
            None
        )
        if not registry:
            raise RegistryError(f"Registry not found: {registry_name}")

        # Download package
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            package_path = registry.download(name, target_version, tmppath)

            # Verify checksum
            version_info = metadata.get_version(target_version)
            if version_info:
                actual_checksum = compute_checksum(package_path)
                if version_info.checksum and actual_checksum != version_info.checksum:
                    raise InstallError(
                        f"Checksum mismatch for {name}@{target_version}. "
                        "Package may be corrupted."
                    )

            # Unpack to skills directory
            install_path = INSTALLED_SKILLS_DIR / name
            if install_path.exists():
                shutil.rmtree(install_path)
            install_path.mkdir(parents=True)

            unpack_skill(package_path, install_path)

        # Record installation
        installed = InstalledSkill(
            name=name,
            version=target_version,
            installed_at=datetime.now().isoformat(),
            source_registry=registry_name,
            path=install_path,
            checksum=version_info.checksum if version_info else "",
        )
        self._installed[name] = installed
        self._save_installed()

        return installed

    def uninstall(self, name: str) -> bool:
        """Uninstall a skill."""
        if name not in self._installed:
            return False

        installed = self._installed[name]
        if installed.path.exists():
            shutil.rmtree(installed.path)

        del self._installed[name]
        self._save_installed()

        return True

    def list_installed(self) -> list[InstalledSkill]:
        """List all installed skills."""
        return list(self._installed.values())

    def get_installed(self, name: str) -> Optional[InstalledSkill]:
        """Get info about an installed skill."""
        return self._installed.get(name)

    def get_installed_path(self, name: str) -> Optional[Path]:
        """Get the path to an installed skill."""
        installed = self._installed.get(name)
        return installed.path if installed else None

    def check_updates(self) -> list[tuple[str, str, str]]:
        """Check for available updates.

        Returns list of (name, installed_version, latest_version) tuples.
        """
        updates = []
        for name, installed in self._installed.items():
            result = self.get_skill(name)
            if result:
                _, metadata = result
                latest = metadata.latest_version
                if latest and parse_version(latest) > parse_version(installed.version):
                    updates.append((name, installed.version, latest))
        return updates


# =============================================================================
# Packaging Functions
# =============================================================================


def compute_checksum(path: Path) -> str:
    """Compute SHA256 checksum of a file."""
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def pack_skill(skill_dir: Path, output_path: Optional[Path] = None) -> Path:
    """Package a skill directory into a tarball.

    Args:
        skill_dir: Path to skill directory
        output_path: Optional output path (default: skill_dir/../name-version.tar.gz)

    Returns:
        Path to created package
    """
    skill_dir = skill_dir.resolve()

    # Load skill metadata
    try:
        skill_data = load_skill_yaml(skill_dir)
    except SkillLoadError as e:
        raise PackageError(f"Cannot load skill: {e}")

    name = skill_data.get("name")
    version = skill_data.get("version", "0.1.0")

    if not name:
        raise PackageError("Skill must have a name")

    if not SKILL_NAME_PATTERN.match(name):
        raise PackageError(
            f"Invalid skill name: {name}. "
            "Must be lowercase alphanumeric with underscores/hyphens."
        )

    # Determine output path
    if output_path is None:
        output_path = skill_dir.parent / f"{name}-{version}.tar.gz"
    else:
        output_path = output_path.resolve()

    # Create tarball
    with tarfile.open(output_path, "w:gz") as tar:
        # Add all files except reports, .git, __pycache__, etc.
        for item in skill_dir.iterdir():
            if item.name in ["reports", ".git", "__pycache__", ".pytest_cache"]:
                continue
            if item.name.endswith(".pyc"):
                continue
            tar.add(item, arcname=item.name)

    return output_path


def unpack_skill(package_path: Path, dest_dir: Path) -> Path:
    """Unpack a skill package to a directory.

    Args:
        package_path: Path to package tarball
        dest_dir: Destination directory

    Returns:
        Path to unpacked skill directory
    """
    if not package_path.exists():
        raise PackageError(f"Package not found: {package_path}")

    dest_dir.mkdir(parents=True, exist_ok=True)

    with tarfile.open(package_path, "r:gz") as tar:
        # Security check: ensure no path traversal
        for member in tar.getmembers():
            if member.name.startswith("/") or ".." in member.name:
                raise PackageError(f"Unsafe path in package: {member.name}")

        tar.extractall(dest_dir)

    return dest_dir


def create_metadata_from_skill(skill_dir: Path, author: str = "") -> SkillMetadata:
    """Create registry metadata from a skill directory.

    Args:
        skill_dir: Path to skill directory
        author: Author name/email

    Returns:
        SkillMetadata for the skill
    """
    try:
        skill_data = load_skill_yaml(skill_dir)
    except SkillLoadError as e:
        raise PackageError(f"Cannot load skill: {e}")

    name = skill_data.get("name", "")
    version = skill_data.get("version", "0.1.0")
    description = skill_data.get("description", "")

    # Create version entry
    version_entry = SkillVersion(
        version=version,
        published_at=datetime.now().isoformat(),
        checksum="",  # Will be set after packaging
        size_bytes=0,
    )

    # Extract tags from metadata
    tags = skill_data.get("metadata", {}).get("tags", [])
    if not tags:
        # Try to infer tags
        tags = []
        requirements = skill_data.get("requirements", {})
        for tool in requirements.get("tools", []):
            tags.append(tool)

    return SkillMetadata(
        name=name,
        description=description,
        author=author,
        tags=tags,
        versions=[version_entry],
        dependencies=skill_data.get("metadata", {}).get("dependencies", {}),
    )


def publish_skill(
    skill_dir: Path,
    registry_name: Optional[str] = None,
    author: str = "",
) -> tuple[Path, SkillMetadata]:
    """Package and publish a skill to a registry.

    Args:
        skill_dir: Path to skill directory
        registry_name: Target registry (default: first local registry)
        author: Author name/email

    Returns:
        Tuple of (package_path, metadata)
    """
    manager = RegistryManager()

    # Find target registry
    if registry_name:
        registry = next(
            (r for r in manager.registries if r.config.name == registry_name),
            None
        )
        if not registry:
            raise RegistryError(f"Registry not found: {registry_name}")
    else:
        # Use first local registry
        registry = next(
            (r for r in manager.registries if r.config.type == "local"),
            None
        )
        if not registry:
            raise RegistryError("No local registry configured")

    # Create metadata
    metadata = create_metadata_from_skill(skill_dir, author)

    # Package skill
    with tempfile.TemporaryDirectory() as tmpdir:
        package_path = pack_skill(skill_dir, Path(tmpdir) / f"{metadata.name}.tar.gz")

        # Update metadata with checksum and size
        checksum = compute_checksum(package_path)
        size = package_path.stat().st_size

        metadata.versions[0].checksum = checksum
        metadata.versions[0].size_bytes = size

        # Publish
        if not registry.publish(package_path, metadata):
            raise PublishError("Failed to publish to registry")

        # Copy package to permanent location
        final_path = REGISTRY_DIR / "published" / f"{metadata.name}-{metadata.versions[0].version}.tar.gz"
        final_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(package_path, final_path)

    return final_path, metadata


# =============================================================================
# Utility Functions
# =============================================================================


def init_registry_dir() -> Path:
    """Initialize the registry directory structure."""
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    INSTALLED_SKILLS_DIR.mkdir(parents=True, exist_ok=True)

    # Create local registry
    local_registry = REGISTRY_DIR / "local"
    local_registry.mkdir(exist_ok=True)
    (local_registry / "packages").mkdir(exist_ok=True)

    # Create default index
    index_file = local_registry / "index.json"
    if not index_file.exists():
        index_file.write_text(json.dumps({"skills": {}, "updated_at": datetime.now().isoformat()}, indent=2))

    return REGISTRY_DIR
