"""Tests for skill scaffolding."""

import pytest
from pathlib import Path
import tempfile

from skillforge.scaffold import (
    create_skill_scaffold,
    add_reference_doc,
    add_script,
    generate_example_script,
    generate_reference_doc,
)
from skillforge.skill import Skill


class TestCreateSkillScaffold:
    """Tests for create_skill_scaffold function."""

    def test_creates_skill_directory(self):
        """Test that scaffold creates skill directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            skill_dir = create_skill_scaffold("my-skill", output_dir)

            assert skill_dir.exists()
            assert skill_dir.is_dir()
            assert skill_dir.name == "my-skill"

    def test_creates_skill_md(self):
        """Test that scaffold creates SKILL.md."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = create_skill_scaffold("test-skill", Path(tmpdir))

            skill_md = skill_dir / "SKILL.md"
            assert skill_md.exists()

    def test_skill_md_is_valid(self):
        """Test that created SKILL.md is valid."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = create_skill_scaffold(
                "valid-skill",
                Path(tmpdir),
                description="A test description. Use when testing.",
            )

            skill = Skill.from_directory(skill_dir)
            assert skill.name == "valid-skill"
            assert "test description" in skill.description

    def test_normalizes_name(self):
        """Test that name is normalized."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = create_skill_scaffold("My Cool Skill", Path(tmpdir))

            assert skill_dir.name == "my-cool-skill"

            skill = Skill.from_directory(skill_dir)
            assert skill.name == "my-cool-skill"

    def test_with_description(self):
        """Test scaffold with custom description."""
        with tempfile.TemporaryDirectory() as tmpdir:
            desc = "Custom description for the skill."
            skill_dir = create_skill_scaffold(
                "desc-test",
                Path(tmpdir),
                description=desc,
            )

            skill = Skill.from_directory(skill_dir)
            assert skill.description == desc

    def test_default_description(self):
        """Test scaffold generates default description."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = create_skill_scaffold("no-desc", Path(tmpdir))

            skill = Skill.from_directory(skill_dir)
            assert "no-desc" in skill.description
            assert "TODO" in skill.description

    def test_with_scripts(self):
        """Test scaffold with scripts directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = create_skill_scaffold(
                "with-scripts",
                Path(tmpdir),
                with_scripts=True,
            )

            scripts_dir = skill_dir / "scripts"
            assert scripts_dir.exists()
            assert scripts_dir.is_dir()

            example = scripts_dir / "example.py"
            assert example.exists()

    def test_example_script_content(self):
        """Test that example script has proper content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = create_skill_scaffold(
                "script-test",
                Path(tmpdir),
                with_scripts=True,
            )

            script = skill_dir / "scripts" / "example.py"
            content = script.read_text()

            assert "#!/usr/bin/env python3" in content
            assert "script-test" in content
            assert "import json" in content

    def test_existing_dir_raises_without_force(self):
        """Test that existing directory raises error without force."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            skill_dir = output_dir / "exists"
            skill_dir.mkdir()

            with pytest.raises(FileExistsError):
                create_skill_scaffold("exists", output_dir)

    def test_force_overwrites(self):
        """Test that force allows overwriting."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            # Create first
            skill_dir1 = create_skill_scaffold(
                "force-test",
                output_dir,
                description="First version",
            )

            # Create again with force
            skill_dir2 = create_skill_scaffold(
                "force-test",
                output_dir,
                description="Second version",
                force=True,
            )

            skill = Skill.from_directory(skill_dir2)
            assert "Second version" in skill.description

    def test_invalid_name_raises(self):
        """Test that invalid name raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Name that becomes empty after normalization
            with pytest.raises(ValueError, match="Invalid skill name"):
                create_skill_scaffold("@#$%", Path(tmpdir))


class TestAddReferenceDoc:
    """Tests for add_reference_doc function."""

    def test_add_reference_doc(self):
        """Test adding a reference document."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = create_skill_scaffold("ref-test", Path(tmpdir))

            doc_path = add_reference_doc(skill_dir, "REFERENCE")

            assert doc_path.exists()
            assert doc_path.name == "REFERENCE.md"
            assert doc_path.parent == skill_dir

    def test_auto_adds_md_extension(self):
        """Test that .md extension is added if missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = create_skill_scaffold("ext-test", Path(tmpdir))

            doc_path = add_reference_doc(skill_dir, "API-DOCS")

            assert doc_path.name == "API-DOCS.md"

    def test_keeps_md_extension(self):
        """Test that .md extension is not duplicated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = create_skill_scaffold("md-test", Path(tmpdir))

            doc_path = add_reference_doc(skill_dir, "README.md")

            assert doc_path.name == "README.md"

    def test_custom_content(self):
        """Test adding custom content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = create_skill_scaffold("custom", Path(tmpdir))

            custom = "# Custom Content\n\nMy custom documentation."
            doc_path = add_reference_doc(skill_dir, "CUSTOM", content=custom)

            assert doc_path.read_text() == custom


class TestAddScript:
    """Tests for add_script function."""

    def test_add_python_script(self):
        """Test adding a Python script."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = create_skill_scaffold("py-script", Path(tmpdir))

            script_path = add_script(skill_dir, "helper", language="python")

            assert script_path.exists()
            assert script_path.name == "helper.py"
            assert script_path.parent.name == "scripts"

    def test_add_bash_script(self):
        """Test adding a Bash script."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = create_skill_scaffold("bash-script", Path(tmpdir))

            script_path = add_script(skill_dir, "build", language="bash")

            assert script_path.name == "build.sh"
            content = script_path.read_text()
            assert "#!/bin/bash" in content

    def test_add_node_script(self):
        """Test adding a Node.js script."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = create_skill_scaffold("node-script", Path(tmpdir))

            script_path = add_script(skill_dir, "process", language="node")

            assert script_path.name == "process.js"
            content = script_path.read_text()
            assert "#!/usr/bin/env node" in content

    def test_creates_scripts_dir(self):
        """Test that scripts directory is created if missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create without scripts
            skill_dir = create_skill_scaffold(
                "no-scripts",
                Path(tmpdir),
                with_scripts=False,
            )

            assert not (skill_dir / "scripts").exists()

            add_script(skill_dir, "new-script")

            assert (skill_dir / "scripts").exists()

    def test_custom_script_content(self):
        """Test adding script with custom content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = create_skill_scaffold("custom-script", Path(tmpdir))

            custom = "#!/usr/bin/env python3\nprint('custom')"
            script_path = add_script(skill_dir, "custom", content=custom)

            assert script_path.read_text() == custom


class TestGenerateFunctions:
    """Tests for generation helper functions."""

    def test_generate_example_script(self):
        """Test example script generation."""
        content = generate_example_script("my-skill")

        assert "#!/usr/bin/env python3" in content
        assert "my-skill" in content
        assert "def main()" in content
        assert "json" in content

    def test_generate_reference_doc(self):
        """Test reference doc generation."""
        content = generate_reference_doc("my-skill", "API Reference")

        assert "# API Reference" in content
        assert "my-skill" in content
        assert "## Overview" in content
        assert "## Examples" in content
