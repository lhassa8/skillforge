"""Tests for the Skill model and SKILL.md parsing."""

import pytest
from pathlib import Path
import tempfile

from skillforge.skill import (
    Skill,
    SkillParseError,
    normalize_skill_name,
    generate_skill_content,
    MAX_NAME_LENGTH,
    MAX_DESCRIPTION_LENGTH,
)


class TestSkillParsing:
    """Tests for SKILL.md parsing."""

    def test_parse_valid_skill_md(self):
        """Test parsing a valid SKILL.md file."""
        content = """---
name: test-skill
description: A test skill for unit testing.
---

# Test Skill

This is the skill content.
"""
        skill = Skill.from_skill_md(content)

        assert skill.name == "test-skill"
        assert skill.description == "A test skill for unit testing."
        assert "# Test Skill" in skill.content
        assert "This is the skill content." in skill.content

    def test_parse_multiline_description(self):
        """Test parsing with a multiline description."""
        content = """---
name: multi-line
description: >
  This is a longer description
  that spans multiple lines.
---

Content here.
"""
        skill = Skill.from_skill_md(content)
        assert "longer description" in skill.description
        assert "multiple lines" in skill.description

    def test_missing_frontmatter_raises_error(self):
        """Test that missing frontmatter raises SkillParseError."""
        content = "# Just markdown content"

        with pytest.raises(SkillParseError, match="YAML frontmatter"):
            Skill.from_skill_md(content)

    def test_missing_name_raises_error(self):
        """Test that missing name raises SkillParseError."""
        content = """---
description: Has description but no name.
---

Content.
"""
        with pytest.raises(SkillParseError, match="name"):
            Skill.from_skill_md(content)

    def test_missing_description_raises_error(self):
        """Test that missing description raises SkillParseError."""
        content = """---
name: has-name
---

Content.
"""
        with pytest.raises(SkillParseError, match="description"):
            Skill.from_skill_md(content)

    def test_invalid_yaml_raises_error(self):
        """Test that invalid YAML raises SkillParseError."""
        content = """---
name: [invalid yaml
description: broken
---

Content.
"""
        with pytest.raises(SkillParseError, match="YAML"):
            Skill.from_skill_md(content)


class TestSkillGeneration:
    """Tests for SKILL.md generation."""

    def test_to_skill_md_roundtrip(self):
        """Test that to_skill_md produces parseable output."""
        skill = Skill(
            name="roundtrip-test",
            description="Testing roundtrip conversion.",
            content="# Content\n\nSome markdown here.",
        )

        md_content = skill.to_skill_md()
        parsed = Skill.from_skill_md(md_content)

        assert parsed.name == skill.name
        assert parsed.description == skill.description
        assert parsed.content == skill.content

    def test_generate_skill_content(self):
        """Test default content generation."""
        content = generate_skill_content("my-skill", "Does something useful.")

        assert "My Skill" in content  # Title case conversion
        assert "Does something useful." in content
        assert "## Instructions" in content
        assert "## Examples" in content


class TestSkillValidation:
    """Tests for skill validation."""

    def test_valid_skill_passes(self):
        """Test that a valid skill passes validation."""
        skill = Skill(
            name="valid-skill",
            description="A valid skill description.",
            content="Some content",
        )

        errors = skill.validate()
        assert len(errors) == 0
        assert skill.is_valid()

    def test_empty_name_fails(self):
        """Test that empty name fails validation."""
        skill = Skill(name="", description="Valid description.")

        errors = skill.validate()
        assert any("Name" in e for e in errors)

    def test_name_too_long_fails(self):
        """Test that overly long name fails validation."""
        skill = Skill(
            name="a" * (MAX_NAME_LENGTH + 1),
            description="Valid description.",
        )

        errors = skill.validate()
        assert any(str(MAX_NAME_LENGTH) in e for e in errors)

    def test_name_with_uppercase_fails(self):
        """Test that uppercase in name fails validation."""
        skill = Skill(name="Invalid-Name", description="Valid description.")

        errors = skill.validate()
        assert any("lowercase" in e for e in errors)

    def test_name_with_spaces_fails(self):
        """Test that spaces in name fails validation."""
        skill = Skill(name="invalid name", description="Valid description.")

        errors = skill.validate()
        assert any("lowercase" in e.lower() or "letters" in e.lower() for e in errors)

    def test_reserved_word_fails(self):
        """Test that reserved words fail validation."""
        skill = Skill(name="my-anthropic-skill", description="Valid description.")

        errors = skill.validate()
        assert any("reserved" in e.lower() for e in errors)

        skill2 = Skill(name="claude-helper", description="Valid description.")
        errors2 = skill2.validate()
        assert any("reserved" in e.lower() for e in errors2)

    def test_xml_in_name_fails(self):
        """Test that XML tags in name fail validation."""
        skill = Skill(name="skill<tag>", description="Valid description.")

        errors = skill.validate()
        assert any("XML" in e for e in errors)

    def test_empty_description_fails(self):
        """Test that empty description fails validation."""
        skill = Skill(name="valid-name", description="")

        errors = skill.validate()
        assert any("Description" in e for e in errors)

    def test_description_too_long_fails(self):
        """Test that overly long description fails validation."""
        skill = Skill(
            name="valid-name",
            description="a" * (MAX_DESCRIPTION_LENGTH + 1),
        )

        errors = skill.validate()
        assert any(str(MAX_DESCRIPTION_LENGTH) in e for e in errors)

    def test_xml_in_description_fails(self):
        """Test that XML tags in description fail validation."""
        skill = Skill(
            name="valid-name",
            description="Description with <tag>XML</tag> content.",
        )

        errors = skill.validate()
        assert any("XML" in e for e in errors)


class TestSkillNameNormalization:
    """Tests for skill name normalization."""

    def test_lowercase_conversion(self):
        """Test uppercase to lowercase conversion."""
        assert normalize_skill_name("MySkill") == "myskill"
        assert normalize_skill_name("PDF-Processor") == "pdf-processor"

    def test_space_to_hyphen(self):
        """Test space to hyphen conversion."""
        assert normalize_skill_name("my skill") == "my-skill"
        assert normalize_skill_name("pdf  processor") == "pdf-processor"

    def test_underscore_to_hyphen(self):
        """Test underscore to hyphen conversion."""
        assert normalize_skill_name("my_skill") == "my-skill"
        assert normalize_skill_name("pdf__processor") == "pdf-processor"

    def test_special_chars_removed(self):
        """Test special character removal."""
        assert normalize_skill_name("skill@name!") == "skillname"
        assert normalize_skill_name("skill.name") == "skillname"

    def test_leading_trailing_hyphens_removed(self):
        """Test leading/trailing hyphen removal."""
        assert normalize_skill_name("-skill-") == "skill"
        assert normalize_skill_name("--skill--") == "skill"

    def test_multiple_hyphens_collapsed(self):
        """Test multiple hyphen collapsing."""
        assert normalize_skill_name("my---skill") == "my-skill"

    def test_truncation_at_max_length(self):
        """Test truncation at max length."""
        long_name = "a" * 100
        result = normalize_skill_name(long_name)
        assert len(result) <= MAX_NAME_LENGTH


class TestSkillFromDirectory:
    """Tests for loading skills from directories."""

    def test_load_from_directory(self):
        """Test loading a skill from a directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir)
            skill_md = skill_dir / "SKILL.md"
            skill_md.write_text("""---
name: dir-skill
description: Loaded from directory.
---

# Directory Skill
""")

            skill = Skill.from_directory(skill_dir)

            assert skill.name == "dir-skill"
            assert skill.path == skill_dir

    def test_missing_skill_md_raises_error(self):
        """Test that missing SKILL.md raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir)

            with pytest.raises(SkillParseError, match="SKILL.md not found"):
                Skill.from_directory(skill_dir)

    def test_discovers_additional_files(self):
        """Test discovery of additional markdown files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir)

            (skill_dir / "SKILL.md").write_text("""---
name: multi-file
description: Has extra files.
---

Content.
""")
            (skill_dir / "REFERENCE.md").write_text("# Reference")
            (skill_dir / "API.md").write_text("# API Docs")

            skill = Skill.from_directory(skill_dir)

            assert "REFERENCE.md" in skill.additional_files
            assert "API.md" in skill.additional_files

    def test_discovers_scripts(self):
        """Test discovery of scripts directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir)
            scripts_dir = skill_dir / "scripts"
            scripts_dir.mkdir()

            (skill_dir / "SKILL.md").write_text("""---
name: with-scripts
description: Has scripts.
---

Content.
""")
            (scripts_dir / "helper.py").write_text("# Python script")
            (scripts_dir / "build.sh").write_text("#!/bin/bash")

            skill = Skill.from_directory(skill_dir)

            assert "helper.py" in skill.scripts
            assert "build.sh" in skill.scripts
