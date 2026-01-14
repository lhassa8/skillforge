"""Tests for skill bundling."""

import pytest
from pathlib import Path
import tempfile
import zipfile

from skillforge.bundler import (
    bundle_skill,
    extract_skill,
    list_bundle_contents,
    BundleResult,
)


def create_test_skill(skill_dir: Path, name: str = "test-skill") -> None:
    """Create a minimal test skill in the given directory."""
    (skill_dir / "SKILL.md").write_text(f"""---
name: {name}
description: A test skill for bundling. Use when testing bundler.
---

# {name.replace('-', ' ').title()}

This is a test skill with enough content to pass validation.
""")


class TestBundleSkill:
    """Tests for bundle_skill function."""

    def test_bundle_creates_zip(self):
        """Test that bundling creates a zip file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "my-skill"
            skill_dir.mkdir()
            create_test_skill(skill_dir, "my-skill")

            output_path = Path(tmpdir) / "output.zip"
            result = bundle_skill(skill_dir, output_path)

            assert result.success
            assert result.output_path == output_path
            assert output_path.exists()

    def test_bundle_contains_skill_md(self):
        """Test that bundle contains SKILL.md."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "bundle-test"
            skill_dir.mkdir()
            create_test_skill(skill_dir, "bundle-test")

            output_path = Path(tmpdir) / "bundle.zip"
            result = bundle_skill(skill_dir, output_path)

            assert result.success

            with zipfile.ZipFile(output_path, "r") as zf:
                names = zf.namelist()
                assert "SKILL.md" in names

    def test_bundle_includes_additional_files(self):
        """Test that bundle includes additional markdown files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "multi-file"
            skill_dir.mkdir()
            create_test_skill(skill_dir, "multi-file")
            (skill_dir / "REFERENCE.md").write_text("# Reference")
            (skill_dir / "API.md").write_text("# API Docs")

            output_path = Path(tmpdir) / "bundle.zip"
            result = bundle_skill(skill_dir, output_path)

            assert result.success

            with zipfile.ZipFile(output_path, "r") as zf:
                names = zf.namelist()
                assert "SKILL.md" in names
                assert "REFERENCE.md" in names
                assert "API.md" in names

    def test_bundle_includes_scripts(self):
        """Test that bundle includes scripts directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "with-scripts"
            skill_dir.mkdir()
            create_test_skill(skill_dir, "with-scripts")

            scripts_dir = skill_dir / "scripts"
            scripts_dir.mkdir()
            (scripts_dir / "helper.py").write_text("# Python script")
            (scripts_dir / "build.sh").write_text("#!/bin/bash\necho hello")

            output_path = Path(tmpdir) / "bundle.zip"
            result = bundle_skill(skill_dir, output_path)

            assert result.success

            with zipfile.ZipFile(output_path, "r") as zf:
                names = zf.namelist()
                assert "scripts/helper.py" in names
                assert "scripts/build.sh" in names

    def test_bundle_excludes_hidden_files(self):
        """Test that hidden files are excluded by default."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "hidden-test"
            skill_dir.mkdir()
            create_test_skill(skill_dir, "hidden-test")
            (skill_dir / ".hidden").write_text("Should be excluded")
            (skill_dir / ".git").mkdir()
            (skill_dir / ".git" / "config").write_text("git config")

            output_path = Path(tmpdir) / "bundle.zip"
            result = bundle_skill(skill_dir, output_path)

            assert result.success

            with zipfile.ZipFile(output_path, "r") as zf:
                names = zf.namelist()
                assert ".hidden" not in names
                assert not any(".git" in n for n in names)

    def test_bundle_excludes_pycache(self):
        """Test that __pycache__ is excluded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "pycache-test"
            skill_dir.mkdir()
            create_test_skill(skill_dir, "pycache-test")

            pycache = skill_dir / "scripts" / "__pycache__"
            pycache.mkdir(parents=True)
            (pycache / "module.cpython-311.pyc").write_bytes(b"bytecode")

            output_path = Path(tmpdir) / "bundle.zip"
            result = bundle_skill(skill_dir, output_path)

            assert result.success

            with zipfile.ZipFile(output_path, "r") as zf:
                names = zf.namelist()
                assert not any("__pycache__" in n for n in names)
                assert not any(".pyc" in n for n in names)

    def test_bundle_auto_generates_output_path(self):
        """Test that output path is auto-generated if not provided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "auto-path"
            skill_dir.mkdir()
            create_test_skill(skill_dir, "auto-path")

            result = bundle_skill(skill_dir)

            assert result.success
            assert result.output_path is not None
            assert result.output_path.exists()
            assert "auto-path" in result.output_path.name
            assert result.output_path.suffix == ".zip"

    def test_bundle_reports_file_count(self):
        """Test that bundle reports correct file count."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "count-test"
            skill_dir.mkdir()
            create_test_skill(skill_dir, "count-test")
            (skill_dir / "EXTRA.md").write_text("Extra file")

            result = bundle_skill(skill_dir)

            assert result.success
            assert result.file_count == 2  # SKILL.md + EXTRA.md

    def test_bundle_reports_total_size(self):
        """Test that bundle reports total size."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "size-test"
            skill_dir.mkdir()
            create_test_skill(skill_dir, "size-test")

            result = bundle_skill(skill_dir)

            assert result.success
            assert result.total_size > 0

    def test_bundle_with_validation_failure(self):
        """Test bundle fails when validation fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "invalid"
            skill_dir.mkdir()
            # Create invalid skill (missing description)
            (skill_dir / "SKILL.md").write_text("""---
name: invalid
---

Content.
""")

            result = bundle_skill(skill_dir)

            assert not result.success
            assert "validation" in result.error_message.lower()

    def test_bundle_skip_validation(self):
        """Test bundle can skip validation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "skip-valid"
            skill_dir.mkdir()
            # Create skill that would fail some validation checks
            (skill_dir / "SKILL.md").write_text("""---
name: skip-valid
description: Short desc.
---

Short content.
""")

            result = bundle_skill(skill_dir, validate=False)

            # Should succeed because validation is skipped
            assert result.success


class TestExtractSkill:
    """Tests for extract_skill function."""

    def test_extract_skill(self):
        """Test extracting a skill from zip."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # First create and bundle a skill
            skill_dir = Path(tmpdir) / "original"
            skill_dir.mkdir()
            create_test_skill(skill_dir, "extract-test")
            (skill_dir / "EXTRA.md").write_text("# Extra content")

            zip_path = Path(tmpdir) / "extract-test.zip"
            bundle_skill(skill_dir, zip_path)

            # Now extract it
            output_dir = Path(tmpdir) / "extracted"
            output_dir.mkdir()

            extracted = extract_skill(zip_path, output_dir)

            assert extracted.exists()
            assert (extracted / "SKILL.md").exists()
            assert (extracted / "EXTRA.md").exists()

    def test_extract_preserves_content(self):
        """Test that extraction preserves file content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "content-test"
            skill_dir.mkdir()

            skill_content = """---
name: content-test
description: Testing content preservation. Use when testing.
---

# Special Content

This has special characters: éàü and symbols: @#$%
"""
            (skill_dir / "SKILL.md").write_text(skill_content)

            zip_path = Path(tmpdir) / "content.zip"
            bundle_skill(skill_dir, zip_path)

            output_dir = Path(tmpdir) / "out"
            output_dir.mkdir()
            extracted = extract_skill(zip_path, output_dir)

            content = (extracted / "SKILL.md").read_text()
            assert "content-test" in content
            assert "éàü" in content
            assert "@#$%" in content

    def test_extract_missing_zip_raises(self):
        """Test that missing zip raises FileNotFoundError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(FileNotFoundError):
                extract_skill(Path(tmpdir) / "missing.zip", Path(tmpdir))

    def test_extract_invalid_zip_raises(self):
        """Test that invalid zip raises ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a zip without SKILL.md
            zip_path = Path(tmpdir) / "invalid.zip"
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("random.txt", "Not a skill")

            with pytest.raises(ValueError, match="SKILL.md not found"):
                extract_skill(zip_path, Path(tmpdir))

    def test_extract_existing_dir_without_force_raises(self):
        """Test that extracting to existing dir without force raises."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "exists-test"
            skill_dir.mkdir()
            create_test_skill(skill_dir, "exists-test")

            zip_path = Path(tmpdir) / "exists-test.zip"
            bundle_skill(skill_dir, zip_path)

            output_dir = Path(tmpdir) / "output"
            output_dir.mkdir()
            (output_dir / "exists-test").mkdir()  # Pre-create target

            with pytest.raises(FileExistsError):
                extract_skill(zip_path, output_dir)

    def test_extract_with_force_overwrites(self):
        """Test that force allows overwriting."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "force-test"
            skill_dir.mkdir()
            create_test_skill(skill_dir, "force-test")

            zip_path = Path(tmpdir) / "force-test.zip"
            bundle_skill(skill_dir, zip_path)

            output_dir = Path(tmpdir) / "output"
            output_dir.mkdir()
            existing = output_dir / "force-test"
            existing.mkdir()
            (existing / "old.txt").write_text("Old content")

            extracted = extract_skill(zip_path, output_dir, force=True)

            assert extracted.exists()
            assert (extracted / "SKILL.md").exists()


class TestListBundleContents:
    """Tests for list_bundle_contents function."""

    def test_list_contents(self):
        """Test listing bundle contents."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "list-test"
            skill_dir.mkdir()
            create_test_skill(skill_dir, "list-test")
            (skill_dir / "EXTRA.md").write_text("# Extra")

            zip_path = Path(tmpdir) / "list.zip"
            bundle_skill(skill_dir, zip_path)

            contents = list_bundle_contents(zip_path)

            assert len(contents) == 2
            names = [c["name"] for c in contents]
            assert "SKILL.md" in names
            assert "EXTRA.md" in names

    def test_list_contents_includes_size(self):
        """Test that contents include size info."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "size-info"
            skill_dir.mkdir()
            create_test_skill(skill_dir, "size-info")

            zip_path = Path(tmpdir) / "size.zip"
            bundle_skill(skill_dir, zip_path)

            contents = list_bundle_contents(zip_path)

            for item in contents:
                assert "size" in item
                assert "compressed_size" in item
                assert item["size"] >= item["compressed_size"]

    def test_list_missing_zip_raises(self):
        """Test that missing zip raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            list_bundle_contents(Path("/nonexistent/bundle.zip"))
