"""Tests for skill registry functionality."""

import json
import tarfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import yaml

from skillforge.registry import (
    # Data models
    SkillVersion,
    SkillMetadata,
    RegistryConfig,
    InstalledSkill,
    # Version utilities
    parse_version,
    version_matches,
    find_best_version,
    # Packaging
    compute_checksum,
    pack_skill,
    unpack_skill,
    create_metadata_from_skill,
    # Backends
    LocalRegistryBackend,
    # Manager
    RegistryManager,
    # Exceptions
    RegistryError,
    SkillNotFoundError,
    VersionNotFoundError,
    PackageError,
    # Constants
    SEMVER_PATTERN,
    SKILL_NAME_PATTERN,
)


# =============================================================================
# Version Parsing Tests
# =============================================================================


class TestParseVersion:
    """Tests for semantic version parsing."""

    def test_simple_version(self):
        """Test parsing simple version."""
        major, minor, patch, pre, build = parse_version("1.2.3")
        assert major == 1
        assert minor == 2
        assert patch == 3
        assert pre == ""
        assert build == ""

    def test_prerelease_version(self):
        """Test parsing prerelease version."""
        major, minor, patch, pre, build = parse_version("1.0.0-alpha")
        assert major == 1
        assert minor == 0
        assert patch == 0
        assert pre == "alpha"

    def test_prerelease_with_number(self):
        """Test parsing prerelease with number."""
        major, minor, patch, pre, build = parse_version("1.0.0-beta.1")
        assert pre == "beta.1"

    def test_build_metadata(self):
        """Test parsing build metadata."""
        major, minor, patch, pre, build = parse_version("1.0.0+build.123")
        assert build == "build.123"

    def test_full_version(self):
        """Test parsing full version with prerelease and build."""
        major, minor, patch, pre, build = parse_version("1.2.3-rc.1+build.456")
        assert (major, minor, patch) == (1, 2, 3)
        assert pre == "rc.1"
        assert build == "build.456"

    def test_invalid_version_fallback(self):
        """Test that invalid versions fall back gracefully."""
        major, minor, patch, pre, build = parse_version("invalid")
        assert (major, minor, patch) == (0, 0, 0)
        assert pre == "invalid"


class TestVersionMatches:
    """Tests for version constraint matching."""

    def test_exact_match(self):
        """Test exact version match."""
        assert version_matches("1.2.3", "1.2.3")
        assert not version_matches("1.2.3", "1.2.4")

    def test_wildcard_any(self):
        """Test wildcard for any version."""
        assert version_matches("1.2.3", "*")
        assert version_matches("0.1.0", "*")

    def test_wildcard_minor(self):
        """Test minor version wildcard."""
        assert version_matches("1.2.3", "1.2.*")
        assert version_matches("1.2.99", "1.2.*")
        assert not version_matches("1.3.0", "1.2.*")

    def test_wildcard_major(self):
        """Test major version wildcard."""
        assert version_matches("1.2.3", "1.*")
        assert version_matches("1.99.99", "1.*")
        assert not version_matches("2.0.0", "1.*")

    def test_caret_constraint(self):
        """Test caret (^) constraint."""
        # ^1.2.3 means >=1.2.3, <2.0.0
        assert version_matches("1.2.3", "^1.2.3")
        assert version_matches("1.9.9", "^1.2.3")
        assert not version_matches("2.0.0", "^1.2.3")
        assert not version_matches("1.2.2", "^1.2.3")

    def test_caret_zero_major(self):
        """Test caret constraint with zero major version."""
        # ^0.2.3 means >=0.2.3, <0.3.0
        assert version_matches("0.2.3", "^0.2.3")
        assert version_matches("0.2.9", "^0.2.3")
        assert not version_matches("0.3.0", "^0.2.3")

    def test_tilde_constraint(self):
        """Test tilde (~) constraint."""
        # ~1.2.3 means >=1.2.3, <1.3.0
        assert version_matches("1.2.3", "~1.2.3")
        assert version_matches("1.2.9", "~1.2.3")
        assert not version_matches("1.3.0", "~1.2.3")
        assert not version_matches("1.2.2", "~1.2.3")

    def test_greater_than_or_equal(self):
        """Test >= constraint."""
        assert version_matches("1.2.3", ">=1.2.3")
        assert version_matches("2.0.0", ">=1.2.3")
        assert not version_matches("1.2.2", ">=1.2.3")

    def test_less_than(self):
        """Test < constraint."""
        assert version_matches("1.2.2", "<1.2.3")
        assert not version_matches("1.2.3", "<1.2.3")
        assert not version_matches("2.0.0", "<1.2.3")

    def test_combined_constraints(self):
        """Test combined constraints."""
        assert version_matches("1.5.0", ">=1.0.0,<2.0.0")
        assert not version_matches("2.0.0", ">=1.0.0,<2.0.0")
        assert not version_matches("0.9.9", ">=1.0.0,<2.0.0")

    def test_empty_constraint(self):
        """Test empty constraint matches all."""
        assert version_matches("1.2.3", "")


class TestFindBestVersion:
    """Tests for finding best matching version."""

    def test_find_latest(self):
        """Test finding latest version."""
        versions = ["1.0.0", "1.1.0", "1.2.0", "0.9.0"]
        assert find_best_version(versions) == "1.2.0"

    def test_find_with_constraint(self):
        """Test finding best version with constraint."""
        versions = ["1.0.0", "1.1.0", "2.0.0", "2.1.0"]
        assert find_best_version(versions, "^1.0.0") == "1.1.0"

    def test_no_matching_version(self):
        """Test no matching version returns None."""
        versions = ["1.0.0", "1.1.0"]
        assert find_best_version(versions, ">=2.0.0") is None

    def test_empty_versions(self):
        """Test empty version list returns None."""
        assert find_best_version([]) is None


# =============================================================================
# Data Model Tests
# =============================================================================


class TestSkillVersion:
    """Tests for SkillVersion dataclass."""

    def test_to_dict(self):
        """Test serialization to dictionary."""
        version = SkillVersion(
            version="1.0.0",
            published_at="2024-01-01T00:00:00",
            checksum="abc123",
            size_bytes=1024,
            download_url="https://example.com/pkg.tar.gz",
            changelog="Initial release",
        )
        data = version.to_dict()
        assert data["version"] == "1.0.0"
        assert data["checksum"] == "abc123"
        assert data["download_url"] == "https://example.com/pkg.tar.gz"

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "version": "1.0.0",
            "published_at": "2024-01-01T00:00:00",
            "checksum": "abc123",
            "size_bytes": 1024,
        }
        version = SkillVersion.from_dict(data)
        assert version.version == "1.0.0"
        assert version.checksum == "abc123"


class TestSkillMetadata:
    """Tests for SkillMetadata dataclass."""

    def test_latest_version(self):
        """Test getting latest version."""
        meta = SkillMetadata(
            name="test",
            description="Test skill",
            versions=[
                SkillVersion("0.9.0", "2024-01-01", "a", 100),
                SkillVersion("1.0.0", "2024-01-02", "b", 100),
                SkillVersion("1.1.0", "2024-01-03", "c", 100),
            ],
        )
        assert meta.latest_version == "1.1.0"

    def test_latest_version_empty(self):
        """Test latest version with no versions."""
        meta = SkillMetadata(name="test", description="Test")
        assert meta.latest_version is None

    def test_get_version(self):
        """Test getting specific version."""
        meta = SkillMetadata(
            name="test",
            description="Test",
            versions=[
                SkillVersion("1.0.0", "2024-01-01", "a", 100),
                SkillVersion("1.1.0", "2024-01-02", "b", 100),
            ],
        )
        v = meta.get_version("1.0.0")
        assert v is not None
        assert v.checksum == "a"

    def test_get_version_not_found(self):
        """Test getting non-existent version."""
        meta = SkillMetadata(name="test", description="Test", versions=[])
        assert meta.get_version("1.0.0") is None

    def test_roundtrip(self):
        """Test serialization roundtrip."""
        meta = SkillMetadata(
            name="test-skill",
            description="A test skill",
            author="Test Author",
            license="MIT",
            tags=["test", "example"],
            versions=[SkillVersion("1.0.0", "2024-01-01", "abc", 1024)],
            dependencies={"other-skill": "^1.0.0"},
        )
        data = meta.to_dict()
        restored = SkillMetadata.from_dict(data)
        assert restored.name == meta.name
        assert restored.description == meta.description
        assert restored.author == meta.author
        assert len(restored.versions) == 1


# =============================================================================
# Packaging Tests
# =============================================================================


class TestPackaging:
    """Tests for skill packaging functions."""

    def test_compute_checksum(self, tmp_path):
        """Test computing file checksum."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello world")

        checksum = compute_checksum(test_file)
        assert len(checksum) == 64  # SHA256 hex length
        assert checksum == compute_checksum(test_file)  # Consistent

    def test_pack_skill(self, tmp_path):
        """Test packing a skill into tarball."""
        # Create a skill directory
        skill_dir = tmp_path / "test_skill"
        skill_dir.mkdir()

        skill_yaml = {
            "name": "test-skill",
            "version": "1.0.0",
            "description": "Test skill",
            "steps": [{"id": "s1", "type": "shell", "command": "echo hi"}],
        }
        (skill_dir / "skill.yaml").write_text(yaml.dump(skill_yaml))
        (skill_dir / "SKILL.txt").write_text("Test skill")

        # Pack
        package_path = pack_skill(skill_dir)

        assert package_path.exists()
        assert package_path.suffix == ".gz"
        assert "test-skill-1.0.0" in package_path.name

        # Verify contents
        with tarfile.open(package_path, "r:gz") as tar:
            names = tar.getnames()
            assert "skill.yaml" in names
            assert "SKILL.txt" in names

    def test_pack_skill_excludes_reports(self, tmp_path):
        """Test that packaging excludes reports directory."""
        skill_dir = tmp_path / "test_skill"
        skill_dir.mkdir()

        (skill_dir / "skill.yaml").write_text(
            yaml.dump({"name": "test", "version": "1.0.0", "steps": []})
        )
        (skill_dir / "reports").mkdir()
        (skill_dir / "reports" / "run_123.json").write_text("{}")

        package_path = pack_skill(skill_dir)

        with tarfile.open(package_path, "r:gz") as tar:
            names = tar.getnames()
            assert not any("reports" in n for n in names)

    def test_pack_skill_invalid_name(self, tmp_path):
        """Test packing skill with invalid name raises error."""
        skill_dir = tmp_path / "test_skill"
        skill_dir.mkdir()

        (skill_dir / "skill.yaml").write_text(
            yaml.dump({"name": "Invalid Name!", "version": "1.0.0", "steps": []})
        )

        with pytest.raises(PackageError, match="Invalid skill name"):
            pack_skill(skill_dir)

    def test_unpack_skill(self, tmp_path):
        """Test unpacking a skill tarball."""
        # Create a tarball
        package_path = tmp_path / "test-1.0.0.tar.gz"
        with tarfile.open(package_path, "w:gz") as tar:
            # Add skill.yaml
            skill_yaml = yaml.dump({"name": "test", "version": "1.0.0"})
            info = tarfile.TarInfo(name="skill.yaml")
            info.size = len(skill_yaml.encode())
            from io import BytesIO
            tar.addfile(info, BytesIO(skill_yaml.encode()))

        # Unpack
        dest = tmp_path / "unpacked"
        unpack_skill(package_path, dest)

        assert dest.exists()
        assert (dest / "skill.yaml").exists()

    def test_unpack_skill_path_traversal(self, tmp_path):
        """Test that path traversal is blocked."""
        package_path = tmp_path / "malicious.tar.gz"
        with tarfile.open(package_path, "w:gz") as tar:
            info = tarfile.TarInfo(name="../../../etc/passwd")
            info.size = 4
            from io import BytesIO
            tar.addfile(info, BytesIO(b"test"))

        dest = tmp_path / "unpacked"
        with pytest.raises(PackageError, match="Unsafe path"):
            unpack_skill(package_path, dest)

    def test_create_metadata_from_skill(self, tmp_path):
        """Test creating metadata from skill directory."""
        skill_dir = tmp_path / "test_skill"
        skill_dir.mkdir()

        skill_yaml = {
            "name": "test-skill",
            "version": "1.2.3",
            "description": "A test skill for testing",
            "requirements": {"tools": ["git", "npm"]},
            "steps": [{"id": "s1", "type": "shell", "command": "echo hi"}],
        }
        (skill_dir / "skill.yaml").write_text(yaml.dump(skill_yaml))

        metadata = create_metadata_from_skill(skill_dir, author="Test Author")

        assert metadata.name == "test-skill"
        assert metadata.description == "A test skill for testing"
        assert metadata.author == "Test Author"
        assert len(metadata.versions) == 1
        assert metadata.versions[0].version == "1.2.3"


# =============================================================================
# Local Registry Backend Tests
# =============================================================================


class TestLocalRegistryBackend:
    """Tests for local registry backend."""

    @pytest.fixture
    def local_registry(self, tmp_path):
        """Create a local registry for testing."""
        registry_dir = tmp_path / "registry"
        registry_dir.mkdir()
        (registry_dir / "packages").mkdir()

        # Create initial index
        (registry_dir / "index.json").write_text(json.dumps({
            "skills": {},
            "updated_at": datetime.now().isoformat(),
        }))

        config = RegistryConfig(
            name="test",
            url=str(registry_dir),
            type="local",
        )
        return LocalRegistryBackend(config)

    def test_list_skills_empty(self, local_registry):
        """Test listing skills in empty registry."""
        skills = local_registry.list_skills()
        assert skills == []

    def test_publish_and_list(self, local_registry, tmp_path):
        """Test publishing and listing skills."""
        # Create a skill package
        skill_dir = tmp_path / "my_skill"
        skill_dir.mkdir()
        (skill_dir / "skill.yaml").write_text(yaml.dump({
            "name": "my-skill",
            "version": "1.0.0",
            "description": "Test",
            "steps": [],
        }))

        package_path = pack_skill(skill_dir)
        metadata = create_metadata_from_skill(skill_dir)
        metadata.versions[0].checksum = compute_checksum(package_path)

        # Publish
        local_registry.publish(package_path, metadata)

        # List
        skills = local_registry.list_skills()
        assert len(skills) == 1
        assert skills[0].name == "my-skill"

    def test_search(self, local_registry, tmp_path):
        """Test searching for skills."""
        # Publish a skill
        skill_dir = tmp_path / "docker_setup"
        skill_dir.mkdir()
        (skill_dir / "skill.yaml").write_text(yaml.dump({
            "name": "docker-setup",
            "version": "1.0.0",
            "description": "Set up Docker containers",
            "steps": [],
        }))

        package_path = pack_skill(skill_dir)
        metadata = create_metadata_from_skill(skill_dir)
        metadata.tags = ["docker", "containers"]
        metadata.versions[0].checksum = compute_checksum(package_path)
        local_registry.publish(package_path, metadata)

        # Search by name
        results = local_registry.search("docker")
        assert len(results) == 1
        assert results[0].name == "docker-setup"

        # Search by description
        results = local_registry.search("containers")
        assert len(results) == 1

        # Search with no results
        results = local_registry.search("kubernetes")
        assert len(results) == 0

    def test_get_skill(self, local_registry, tmp_path):
        """Test getting specific skill."""
        # Publish a skill
        skill_dir = tmp_path / "test_skill"
        skill_dir.mkdir()
        (skill_dir / "skill.yaml").write_text(yaml.dump({
            "name": "test-skill",
            "version": "1.0.0",
            "steps": [],
        }))

        package_path = pack_skill(skill_dir)
        metadata = create_metadata_from_skill(skill_dir)
        metadata.versions[0].checksum = compute_checksum(package_path)
        local_registry.publish(package_path, metadata)

        # Get existing
        skill = local_registry.get_skill("test-skill")
        assert skill is not None
        assert skill.name == "test-skill"

        # Get non-existing
        skill = local_registry.get_skill("nonexistent")
        assert skill is None

    def test_download(self, local_registry, tmp_path):
        """Test downloading a skill package."""
        # Publish a skill
        skill_dir = tmp_path / "test_skill"
        skill_dir.mkdir()
        (skill_dir / "skill.yaml").write_text(yaml.dump({
            "name": "test-skill",
            "version": "1.0.0",
            "steps": [],
        }))

        package_path = pack_skill(skill_dir)
        metadata = create_metadata_from_skill(skill_dir)
        metadata.versions[0].checksum = compute_checksum(package_path)
        local_registry.publish(package_path, metadata)

        # Download
        dest = tmp_path / "downloads"
        downloaded = local_registry.download("test-skill", "1.0.0", dest)

        assert downloaded.exists()
        assert downloaded.name == "test-skill-1.0.0.tar.gz"

    def test_download_not_found(self, local_registry, tmp_path):
        """Test downloading non-existent skill."""
        dest = tmp_path / "downloads"
        with pytest.raises(SkillNotFoundError):
            local_registry.download("nonexistent", "1.0.0", dest)


# =============================================================================
# Registry Manager Tests
# =============================================================================


class TestRegistryManager:
    """Tests for RegistryManager."""

    @pytest.fixture
    def manager_with_local(self, tmp_path, monkeypatch):
        """Create a manager with local registry."""
        # Override config directory
        config_dir = tmp_path / ".skillforge"
        config_dir.mkdir()

        monkeypatch.setattr("skillforge.registry.CONFIG_DIR", config_dir)
        monkeypatch.setattr("skillforge.registry.REGISTRY_DIR", config_dir / "registry")
        monkeypatch.setattr("skillforge.registry.INSTALLED_SKILLS_DIR", config_dir / "skills")
        monkeypatch.setattr("skillforge.registry.REGISTRY_CONFIG_FILE", config_dir / "registries.yaml")

        # Create local registry
        local_registry = config_dir / "registry" / "local"
        local_registry.mkdir(parents=True)
        (local_registry / "packages").mkdir()
        (local_registry / "index.json").write_text(json.dumps({"skills": {}}))

        # Create config
        config = {
            "registries": [
                {
                    "name": "local",
                    "url": str(local_registry),
                    "type": "local",
                    "enabled": True,
                    "priority": 100,
                }
            ]
        }
        (config_dir / "registries.yaml").write_text(yaml.dump(config))

        return RegistryManager()

    def test_list_registries(self, manager_with_local):
        """Test listing configured registries."""
        registries = manager_with_local.list_registries()
        assert len(registries) == 1
        assert registries[0].name == "local"

    def test_search_empty(self, manager_with_local):
        """Test searching empty registry."""
        results = manager_with_local.search("test")
        assert results == []

    def test_list_installed_empty(self, manager_with_local):
        """Test listing installed skills when none installed."""
        installed = manager_with_local.list_installed()
        assert installed == []


# =============================================================================
# Pattern Tests
# =============================================================================


class TestPatterns:
    """Tests for regex patterns."""

    def test_semver_pattern_valid(self):
        """Test valid semantic versions."""
        valid_versions = [
            "0.0.0",
            "1.0.0",
            "1.2.3",
            "10.20.30",
            "1.0.0-alpha",
            "1.0.0-alpha.1",
            "1.0.0-0.3.7",
            "1.0.0+build",
            "1.0.0+build.123",
            "1.0.0-beta+build.456",
        ]
        for v in valid_versions:
            assert SEMVER_PATTERN.match(v), f"{v} should match"

    def test_semver_pattern_invalid(self):
        """Test invalid semantic versions."""
        invalid_versions = [
            "1",
            "1.0",
            "v1.0.0",
            "1.0.0.0",
            "01.0.0",
            "1.01.0",
        ]
        for v in invalid_versions:
            assert not SEMVER_PATTERN.match(v), f"{v} should not match"

    def test_skill_name_pattern_valid(self):
        """Test valid skill names."""
        valid_names = [
            "skill",
            "my-skill",
            "my_skill",
            "skill123",
            "a",
        ]
        for name in valid_names:
            assert SKILL_NAME_PATTERN.match(name), f"{name} should match"

    def test_skill_name_pattern_invalid(self):
        """Test invalid skill names."""
        invalid_names = [
            "Skill",  # uppercase
            "123skill",  # starts with number
            "-skill",  # starts with hyphen
            "_skill",  # starts with underscore
            "my skill",  # space
            "skill!",  # special char
        ]
        for name in invalid_names:
            assert not SKILL_NAME_PATTERN.match(name), f"{name} should not match"
