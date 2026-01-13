"""Tests for the scaffold module."""

import pytest
import yaml

from skillforge.scaffold import (
    generate_skill_yaml,
    generate_skill_txt,
    generate_checks_py,
    generate_fixture_yaml,
    create_skill_scaffold,
    validate_skill_name,
)


class TestGenerateSkillYaml:
    """Tests for skill.yaml generation."""

    def test_generates_valid_yaml(self):
        """Test that generated content is valid YAML."""
        content = generate_skill_yaml("test_skill")
        parsed = yaml.safe_load(content)

        assert parsed is not None
        assert isinstance(parsed, dict)

    def test_includes_required_fields(self):
        """Test that generated YAML includes required fields."""
        content = generate_skill_yaml("test_skill")
        parsed = yaml.safe_load(content)

        assert parsed["name"] == "test_skill"
        assert "version" in parsed
        assert "steps" in parsed
        assert "inputs" in parsed

    def test_includes_description(self):
        """Test that custom description is included."""
        content = generate_skill_yaml("test_skill", description="My custom description")
        parsed = yaml.safe_load(content)

        assert parsed["description"] == "My custom description"

    def test_has_default_step(self):
        """Test that a default example step is included."""
        content = generate_skill_yaml("test_skill")
        parsed = yaml.safe_load(content)

        assert len(parsed["steps"]) > 0
        assert parsed["steps"][0]["type"] == "shell"

    def test_has_target_dir_input(self):
        """Test that target_dir input is included."""
        content = generate_skill_yaml("test_skill")
        parsed = yaml.safe_load(content)

        input_names = [i["name"] for i in parsed["inputs"]]
        assert "target_dir" in input_names


class TestGenerateSkillTxt:
    """Tests for SKILL.txt generation."""

    def test_includes_skill_name(self):
        """Test that skill name is in the output."""
        content = generate_skill_txt("my_skill")
        assert "my_skill" in content

    def test_includes_sections(self):
        """Test that required sections are present."""
        content = generate_skill_txt("test_skill")

        assert "DESCRIPTION" in content
        assert "PRECONDITIONS" in content
        assert "INPUTS" in content
        assert "STEPS" in content

    def test_includes_description(self):
        """Test that custom description is included."""
        content = generate_skill_txt("test_skill", description="Custom desc")
        assert "Custom desc" in content


class TestGenerateChecksPy:
    """Tests for checks.py generation."""

    def test_is_valid_python(self):
        """Test that generated content is valid Python."""
        content = generate_checks_py("test_skill")
        # This will raise SyntaxError if invalid
        compile(content, "<string>", "exec")

    def test_includes_skill_name(self):
        """Test that skill name is in docstring."""
        content = generate_checks_py("my_skill")
        assert "my_skill" in content

    def test_has_custom_check_function(self):
        """Test that a custom_check function is defined."""
        content = generate_checks_py("test_skill")
        assert "def custom_check" in content


class TestGenerateFixtureYaml:
    """Tests for fixture.yaml generation."""

    def test_generates_content(self):
        """Test that fixture.yaml content is generated."""
        content = generate_fixture_yaml()
        assert len(content) > 0
        assert "inputs" in content.lower() or "fixture" in content.lower()


class TestValidateSkillName:
    """Tests for skill name validation."""

    def test_valid_simple_name(self):
        """Test that simple names are valid."""
        is_valid, msg = validate_skill_name("my_skill")
        assert is_valid is True

    def test_valid_name_with_numbers(self):
        """Test that names with numbers are valid."""
        is_valid, msg = validate_skill_name("skill123")
        assert is_valid is True

    def test_empty_name_invalid(self):
        """Test that empty names are invalid."""
        is_valid, msg = validate_skill_name("")
        assert is_valid is False
        assert "empty" in msg.lower()

    def test_too_long_name_invalid(self):
        """Test that very long names are invalid."""
        is_valid, msg = validate_skill_name("a" * 101)
        assert is_valid is False
        assert "long" in msg.lower()

    def test_special_chars_only_invalid(self):
        """Test that names with only special chars are invalid."""
        is_valid, msg = validate_skill_name("---")
        assert is_valid is False


class TestCreateSkillScaffold:
    """Tests for scaffold creation."""

    def test_creates_directory_structure(self, tmp_path):
        """Test that all directories are created."""
        skill_dir = create_skill_scaffold("test_skill", tmp_path)

        assert skill_dir.exists()
        assert (skill_dir / "fixtures").exists()
        assert (skill_dir / "fixtures" / "happy_path").exists()
        assert (skill_dir / "fixtures" / "happy_path" / "input").exists()
        assert (skill_dir / "fixtures" / "happy_path" / "expected").exists()
        assert (skill_dir / "reports").exists()
        assert (skill_dir / "cassettes").exists()

    def test_creates_required_files(self, tmp_path):
        """Test that all required files are created."""
        skill_dir = create_skill_scaffold("test_skill", tmp_path)

        assert (skill_dir / "skill.yaml").exists()
        assert (skill_dir / "SKILL.txt").exists()
        assert (skill_dir / "checks.py").exists()

    def test_skill_yaml_is_valid(self, tmp_path):
        """Test that created skill.yaml is valid YAML."""
        skill_dir = create_skill_scaffold("test_skill", tmp_path)

        with open(skill_dir / "skill.yaml") as f:
            parsed = yaml.safe_load(f)

        assert parsed["name"] == "test_skill"

    def test_normalizes_skill_name(self, tmp_path):
        """Test that skill names are normalized."""
        skill_dir = create_skill_scaffold("My Cool Skill!", tmp_path)

        assert skill_dir.name == "my_cool_skill"

    def test_raises_if_exists(self, tmp_path):
        """Test that FileExistsError is raised if directory exists."""
        create_skill_scaffold("test_skill", tmp_path)

        with pytest.raises(FileExistsError):
            create_skill_scaffold("test_skill", tmp_path)

    def test_force_overwrites(self, tmp_path):
        """Test that force=True overwrites existing directory."""
        skill_dir = create_skill_scaffold("test_skill", tmp_path)

        # Modify a file
        (skill_dir / "SKILL.txt").write_text("modified")

        # Recreate with force
        skill_dir2 = create_skill_scaffold("test_skill", tmp_path, force=True)

        assert skill_dir == skill_dir2
        content = (skill_dir / "SKILL.txt").read_text()
        assert "modified" not in content

    def test_includes_description(self, tmp_path):
        """Test that description is included in generated files."""
        skill_dir = create_skill_scaffold(
            "test_skill", tmp_path, description="My description"
        )

        skill_txt = (skill_dir / "SKILL.txt").read_text()
        assert "My description" in skill_txt

        with open(skill_dir / "skill.yaml") as f:
            parsed = yaml.safe_load(f)
        assert parsed["description"] == "My description"
