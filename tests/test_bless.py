"""Tests for the bless command."""

import json
import pytest
import yaml

from skillforge.bless import (
    BlessResult,
    bless_fixture,
    get_golden_info,
)


def create_test_skill(tmp_path, skill_data: dict, name: str = "test_skill"):
    """Helper to create a test skill directory."""
    skill_dir = tmp_path / name
    skill_dir.mkdir()
    (skill_dir / "skill.yaml").write_text(yaml.dump(skill_data))
    (skill_dir / "fixtures").mkdir()
    (skill_dir / "reports").mkdir()
    return skill_dir


def create_fixture(skill_dir, fixture_name: str, input_files: dict = None):
    """Helper to create a fixture directory."""
    fixture_dir = skill_dir / "fixtures" / fixture_name
    fixture_dir.mkdir(parents=True)

    # Create input directory
    input_dir = fixture_dir / "input"
    input_dir.mkdir()

    if input_files:
        for filename, content in input_files.items():
            file_path = input_dir / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)

    return fixture_dir


class TestBlessFixture:
    """Tests for bless_fixture function."""

    def test_successful_bless(self, tmp_path):
        """Test successful blessing of a fixture."""
        skill_dir = create_test_skill(tmp_path, {
            "name": "test_skill",
            "inputs": [{"name": "target_dir", "type": "path"}],
            "steps": [
                {"id": "step1", "type": "shell", "command": "echo hello > output.txt", "cwd": "{sandbox_dir}"},
            ],
            "checks": [],
        })
        create_fixture(skill_dir, "happy_path", {"README.md": "# Test"})

        result = bless_fixture(skill_dir, "happy_path")

        assert result.success is True
        assert result.fixture_name == "happy_path"
        assert "output.txt" in result.changed_files
        assert "README.md" in result.changed_files

    def test_creates_golden_directory(self, tmp_path):
        """Test that golden directory is created."""
        skill_dir = create_test_skill(tmp_path, {
            "name": "test_skill",
            "inputs": [{"name": "target_dir", "type": "path"}],
            "steps": [
                {"id": "step1", "type": "shell", "command": "echo test"},
            ],
            "checks": [],
        })
        create_fixture(skill_dir, "happy_path", {"test.txt": "test"})

        result = bless_fixture(skill_dir, "happy_path")

        golden_dir = skill_dir / "fixtures" / "happy_path" / "_golden"
        assert golden_dir.is_dir()
        assert (golden_dir / "expected_changed_files.json").exists()
        assert (golden_dir / "expected_hashes.json").exists()
        assert (golden_dir / "bless_metadata.json").exists()

    def test_expected_changed_files_content(self, tmp_path):
        """Test expected_changed_files.json content."""
        skill_dir = create_test_skill(tmp_path, {
            "name": "test_skill",
            "inputs": [{"name": "target_dir", "type": "path"}],
            "steps": [
                {"id": "step1", "type": "shell", "command": "echo hello > new_file.txt", "cwd": "{sandbox_dir}"},
            ],
            "checks": [],
        })
        create_fixture(skill_dir, "happy_path", {"existing.txt": "existing"})

        bless_fixture(skill_dir, "happy_path")

        golden_dir = skill_dir / "fixtures" / "happy_path" / "_golden"
        with open(golden_dir / "expected_changed_files.json") as f:
            changed_files = json.load(f)

        assert "existing.txt" in changed_files
        assert "new_file.txt" in changed_files

    def test_expected_hashes_content(self, tmp_path):
        """Test expected_hashes.json content."""
        skill_dir = create_test_skill(tmp_path, {
            "name": "test_skill",
            "inputs": [{"name": "target_dir", "type": "path"}],
            "steps": [
                {"id": "step1", "type": "shell", "command": "echo test"},
            ],
            "checks": [],
        })
        create_fixture(skill_dir, "happy_path", {"test.txt": "test content"})

        bless_fixture(skill_dir, "happy_path")

        golden_dir = skill_dir / "fixtures" / "happy_path" / "_golden"
        with open(golden_dir / "expected_hashes.json") as f:
            hashes = json.load(f)

        assert "test.txt" in hashes
        assert len(hashes["test.txt"]) == 64  # SHA256 hex length

    def test_bless_metadata_content(self, tmp_path):
        """Test bless_metadata.json content."""
        skill_dir = create_test_skill(tmp_path, {
            "name": "my_skill",
            "inputs": [{"name": "target_dir", "type": "path"}],
            "steps": [
                {"id": "step1", "type": "shell", "command": "echo test"},
            ],
            "checks": [],
        })
        create_fixture(skill_dir, "happy_path", {"test.txt": "test"})

        bless_fixture(skill_dir, "happy_path")

        golden_dir = skill_dir / "fixtures" / "happy_path" / "_golden"
        with open(golden_dir / "bless_metadata.json") as f:
            metadata = json.load(f)

        assert "blessed_at" in metadata
        assert "run_id" in metadata
        assert metadata["skill_name"] == "my_skill"
        assert "steps_count" in metadata
        assert "checks_count" in metadata

    def test_fixture_not_found(self, tmp_path):
        """Test error when fixture doesn't exist."""
        skill_dir = create_test_skill(tmp_path, {
            "name": "test_skill",
            "steps": [],
            "checks": [],
        })

        result = bless_fixture(skill_dir, "nonexistent")

        assert result.success is False
        assert "not found" in result.error_message.lower()

    def test_fixture_without_input_dir(self, tmp_path):
        """Test error when fixture has no input directory."""
        skill_dir = create_test_skill(tmp_path, {
            "name": "test_skill",
            "steps": [],
            "checks": [],
        })
        # Create fixture without input dir
        fixture_dir = skill_dir / "fixtures" / "broken"
        fixture_dir.mkdir(parents=True)

        result = bless_fixture(skill_dir, "broken")

        assert result.success is False
        assert "input" in result.error_message.lower()

    def test_skill_execution_failure(self, tmp_path):
        """Test handling of skill execution failure."""
        skill_dir = create_test_skill(tmp_path, {
            "name": "test_skill",
            "inputs": [{"name": "target_dir", "type": "path"}],
            "steps": [
                {"id": "step1", "type": "shell", "command": "exit 1"},
            ],
            "checks": [],
        })
        create_fixture(skill_dir, "happy_path", {"test.txt": "test"})

        result = bless_fixture(skill_dir, "happy_path")

        assert result.success is False
        assert "failed" in result.error_message.lower()

    def test_overwrites_existing_golden(self, tmp_path):
        """Test that bless overwrites existing golden artifacts."""
        skill_dir = create_test_skill(tmp_path, {
            "name": "test_skill",
            "inputs": [{"name": "target_dir", "type": "path"}],
            "steps": [
                {"id": "step1", "type": "shell", "command": "echo first > output.txt", "cwd": "{sandbox_dir}"},
            ],
            "checks": [],
        })
        create_fixture(skill_dir, "happy_path", {"test.txt": "test"})

        # First bless
        bless_fixture(skill_dir, "happy_path")

        golden_dir = skill_dir / "fixtures" / "happy_path" / "_golden"
        with open(golden_dir / "expected_hashes.json") as f:
            first_hashes = json.load(f)

        # Modify the skill
        skill_data = {
            "name": "test_skill",
            "inputs": [{"name": "target_dir", "type": "path"}],
            "steps": [
                {"id": "step1", "type": "shell", "command": "echo second > output.txt", "cwd": "{sandbox_dir}"},
            ],
            "checks": [],
        }
        (skill_dir / "skill.yaml").write_text(yaml.dump(skill_data))

        # Second bless
        bless_fixture(skill_dir, "happy_path")

        with open(golden_dir / "expected_hashes.json") as f:
            second_hashes = json.load(f)

        # Hashes should be different
        assert first_hashes["output.txt"] != second_hashes["output.txt"]

    def test_nested_file_structure(self, tmp_path):
        """Test blessing with nested file structure."""
        skill_dir = create_test_skill(tmp_path, {
            "name": "test_skill",
            "inputs": [{"name": "target_dir", "type": "path"}],
            "steps": [
                {"id": "step1", "type": "shell", "command": "mkdir -p subdir && echo nested > subdir/nested.txt", "cwd": "{sandbox_dir}"},
            ],
            "checks": [],
        })
        create_fixture(skill_dir, "happy_path", {"root.txt": "root"})

        result = bless_fixture(skill_dir, "happy_path")

        assert result.success is True
        assert "subdir/nested.txt" in result.changed_files


class TestGetGoldenInfo:
    """Tests for get_golden_info function."""

    def test_no_golden_artifacts(self, tmp_path):
        """Test when no golden artifacts exist."""
        skill_dir = create_test_skill(tmp_path, {
            "name": "test_skill",
            "steps": [],
            "checks": [],
        })
        create_fixture(skill_dir, "happy_path", {"test.txt": "test"})

        info = get_golden_info(skill_dir, "happy_path")

        assert info == {}

    def test_existing_golden_artifacts(self, tmp_path):
        """Test when golden artifacts exist."""
        skill_dir = create_test_skill(tmp_path, {
            "name": "test_skill",
            "inputs": [{"name": "target_dir", "type": "path"}],
            "steps": [
                {"id": "step1", "type": "shell", "command": "echo test"},
            ],
            "checks": [],
        })
        create_fixture(skill_dir, "happy_path", {"test.txt": "test"})

        # Bless to create golden artifacts
        bless_fixture(skill_dir, "happy_path")

        info = get_golden_info(skill_dir, "happy_path")

        assert info["exists"] is True
        assert "path" in info
        assert "metadata" in info
        assert "file_count" in info

    def test_golden_info_with_metadata(self, tmp_path):
        """Test golden info includes metadata details."""
        skill_dir = create_test_skill(tmp_path, {
            "name": "my_skill",
            "inputs": [{"name": "target_dir", "type": "path"}],
            "steps": [
                {"id": "step1", "type": "shell", "command": "echo test"},
            ],
            "checks": [],
        })
        create_fixture(skill_dir, "happy_path", {"test.txt": "test"})

        bless_fixture(skill_dir, "happy_path")
        info = get_golden_info(skill_dir, "happy_path")

        assert info["metadata"]["skill_name"] == "my_skill"
        assert "blessed_at" in info["metadata"]


class TestBlessResult:
    """Tests for BlessResult dataclass."""

    def test_default_values(self):
        """Test default values."""
        result = BlessResult(fixture_name="test")

        assert result.fixture_name == "test"
        assert result.success is False
        assert result.error_message == ""
        assert result.run_report is None
        assert result.changed_files == []
        assert result.golden_dir == ""

    def test_changed_files_initialization(self):
        """Test that changed_files is properly initialized."""
        result1 = BlessResult(fixture_name="test1")
        result2 = BlessResult(fixture_name="test2")

        # Ensure they have separate lists
        result1.changed_files.append("file1.txt")

        assert "file1.txt" in result1.changed_files
        assert "file1.txt" not in result2.changed_files
