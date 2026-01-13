"""Tests for the skill loader module."""

import pytest
import yaml

from skillforge.loader import (
    load_skill_yaml,
    get_skill_files,
    list_fixtures,
    SkillLoadError,
)


class TestLoadSkillYaml:
    """Tests for load_skill_yaml function."""

    def test_loads_valid_yaml(self, tmp_path):
        """Test loading a valid skill.yaml file."""
        skill_dir = tmp_path / "my_skill"
        skill_dir.mkdir()

        skill_data = {
            "name": "my_skill",
            "version": "1.0.0",
            "steps": [],
            "inputs": [],
        }
        (skill_dir / "skill.yaml").write_text(yaml.dump(skill_data))

        result = load_skill_yaml(skill_dir)

        assert result["name"] == "my_skill"
        assert result["version"] == "1.0.0"

    def test_raises_if_directory_not_found(self, tmp_path):
        """Test that SkillLoadError is raised for missing directory."""
        with pytest.raises(SkillLoadError) as exc_info:
            load_skill_yaml(tmp_path / "nonexistent")

        assert "not found" in str(exc_info.value)

    def test_raises_if_skill_yaml_not_found(self, tmp_path):
        """Test that SkillLoadError is raised for missing skill.yaml."""
        skill_dir = tmp_path / "my_skill"
        skill_dir.mkdir()

        with pytest.raises(SkillLoadError) as exc_info:
            load_skill_yaml(skill_dir)

        assert "skill.yaml not found" in str(exc_info.value)

    def test_raises_for_invalid_yaml(self, tmp_path):
        """Test that SkillLoadError is raised for invalid YAML."""
        skill_dir = tmp_path / "my_skill"
        skill_dir.mkdir()
        (skill_dir / "skill.yaml").write_text("invalid: yaml: content:")

        with pytest.raises(SkillLoadError) as exc_info:
            load_skill_yaml(skill_dir)

        assert "Invalid YAML" in str(exc_info.value)

    def test_raises_for_empty_yaml(self, tmp_path):
        """Test that SkillLoadError is raised for empty file."""
        skill_dir = tmp_path / "my_skill"
        skill_dir.mkdir()
        (skill_dir / "skill.yaml").write_text("")

        with pytest.raises(SkillLoadError) as exc_info:
            load_skill_yaml(skill_dir)

        assert "empty" in str(exc_info.value)

    def test_raises_for_non_mapping(self, tmp_path):
        """Test that SkillLoadError is raised for non-mapping YAML."""
        skill_dir = tmp_path / "my_skill"
        skill_dir.mkdir()
        (skill_dir / "skill.yaml").write_text("- item1\n- item2")

        with pytest.raises(SkillLoadError) as exc_info:
            load_skill_yaml(skill_dir)

        assert "mapping" in str(exc_info.value)


class TestGetSkillFiles:
    """Tests for get_skill_files function."""

    def test_returns_existence_status(self, tmp_path):
        """Test that file existence is correctly reported."""
        skill_dir = tmp_path / "my_skill"
        skill_dir.mkdir()
        (skill_dir / "skill.yaml").write_text("name: test")
        (skill_dir / "fixtures").mkdir()

        result = get_skill_files(skill_dir)

        assert result["skill.yaml"] is True
        assert result["SKILL.txt"] is False
        assert result["fixtures"] is True

    def test_checks_all_expected_files(self, tmp_path):
        """Test that all expected files are checked."""
        skill_dir = tmp_path / "my_skill"
        skill_dir.mkdir()

        result = get_skill_files(skill_dir)

        expected_keys = [
            "skill.yaml",
            "SKILL.txt",
            "checks.py",
            "fixtures",
            "fixtures/happy_path",
            "cassettes",
            "reports",
        ]
        for key in expected_keys:
            assert key in result


class TestListFixtures:
    """Tests for list_fixtures function."""

    def test_lists_fixture_directories(self, tmp_path):
        """Test that fixture directories are listed."""
        skill_dir = tmp_path / "my_skill"
        fixtures_dir = skill_dir / "fixtures"
        fixtures_dir.mkdir(parents=True)
        (fixtures_dir / "happy_path").mkdir()
        (fixtures_dir / "edge_case").mkdir()

        result = list_fixtures(skill_dir)

        assert "happy_path" in result
        assert "edge_case" in result

    def test_returns_empty_for_no_fixtures(self, tmp_path):
        """Test that empty list is returned when no fixtures exist."""
        skill_dir = tmp_path / "my_skill"
        skill_dir.mkdir()

        result = list_fixtures(skill_dir)

        assert result == []

    def test_ignores_hidden_directories(self, tmp_path):
        """Test that hidden directories are ignored."""
        skill_dir = tmp_path / "my_skill"
        fixtures_dir = skill_dir / "fixtures"
        fixtures_dir.mkdir(parents=True)
        (fixtures_dir / ".hidden").mkdir()
        (fixtures_dir / "visible").mkdir()

        result = list_fixtures(skill_dir)

        assert ".hidden" not in result
        assert "visible" in result

    def test_ignores_files(self, tmp_path):
        """Test that files are ignored (only directories)."""
        skill_dir = tmp_path / "my_skill"
        fixtures_dir = skill_dir / "fixtures"
        fixtures_dir.mkdir(parents=True)
        (fixtures_dir / "not_a_fixture.txt").write_text("test")
        (fixtures_dir / "happy_path").mkdir()

        result = list_fixtures(skill_dir)

        assert "not_a_fixture.txt" not in result
        assert "happy_path" in result
