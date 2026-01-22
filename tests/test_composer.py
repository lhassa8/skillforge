"""Tests for skill composition functionality."""

import pytest
from pathlib import Path
from typer.testing import CliRunner

from skillforge.composer import (
    compose_skill,
    get_includes,
    resolve_includes,
    validate_composition,
    has_includes,
    CompositionResult,
    CompositionError,
    CircularDependencyError,
)
from skillforge.skill import Skill
from skillforge.cli import app


runner = CliRunner()


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def simple_skill(tmp_path: Path) -> Path:
    """Create a simple skill without includes."""
    skill_dir = tmp_path / "simple-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("""---
name: simple-skill
description: A simple skill without includes
---

# Simple Skill

This is a simple skill with no includes.

## Instructions

Do something simple.
""")
    return skill_dir


@pytest.fixture
def component_a(tmp_path: Path) -> Path:
    """Create component skill A."""
    skill_dir = tmp_path / "components" / "component-a"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("""---
name: component-a
description: Component A skill
---

# Component A

This is component A.

## Instructions for A

Do thing A.
""")
    return skill_dir


@pytest.fixture
def component_b(tmp_path: Path) -> Path:
    """Create component skill B."""
    skill_dir = tmp_path / "components" / "component-b"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("""---
name: component-b
description: Component B skill
---

# Component B

This is component B.

## Instructions for B

Do thing B.
""")
    return skill_dir


@pytest.fixture
def composite_skill(tmp_path: Path, component_a: Path, component_b: Path) -> Path:
    """Create a composite skill with includes."""
    skill_dir = tmp_path / "composite-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("""---
name: composite-skill
description: A composite skill with includes
includes:
  - ../components/component-a
  - ../components/component-b
---

# Composite Skill

This skill combines A and B.

## Overview

Main instructions here.
""")
    return skill_dir


@pytest.fixture
def nested_composite(tmp_path: Path, composite_skill: Path, component_a: Path) -> Path:
    """Create a nested composite (includes another composite)."""
    skill_dir = tmp_path / "nested-composite"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("""---
name: nested-composite
description: A nested composite skill
includes:
  - ../composite-skill
---

# Nested Composite

This includes another composite.
""")
    return skill_dir


@pytest.fixture
def circular_a(tmp_path: Path) -> Path:
    """Create circular dependency skill A (depends on B)."""
    skill_dir = tmp_path / "circular" / "circular-a"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("""---
name: circular-a
description: Circular A
includes:
  - ../circular-b
---

# Circular A
""")
    return skill_dir


@pytest.fixture
def circular_b(tmp_path: Path, circular_a: Path) -> Path:
    """Create circular dependency skill B (depends on A)."""
    skill_dir = tmp_path / "circular" / "circular-b"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("""---
name: circular-b
description: Circular B
includes:
  - ../circular-a
---

# Circular B
""")
    return skill_dir


# =============================================================================
# has_includes Tests
# =============================================================================


class TestHasIncludes:
    """Tests for has_includes function."""

    def test_skill_without_includes(self, simple_skill: Path):
        """Skill without includes returns False."""
        assert has_includes(simple_skill) is False

    def test_skill_with_includes(self, composite_skill: Path):
        """Skill with includes returns True."""
        assert has_includes(composite_skill) is True

    def test_nonexistent_skill(self, tmp_path: Path):
        """Nonexistent skill returns False."""
        assert has_includes(tmp_path / "nonexistent") is False


# =============================================================================
# get_includes Tests
# =============================================================================


class TestGetIncludes:
    """Tests for get_includes function."""

    def test_no_includes(self, simple_skill: Path):
        """Skill without includes returns empty list."""
        includes = get_includes(simple_skill)
        assert includes == []

    def test_with_includes(self, composite_skill: Path):
        """Skill with includes returns resolved paths."""
        includes = get_includes(composite_skill)
        assert len(includes) == 2
        assert all(isinstance(p, Path) for p in includes)

    def test_nonexistent_skill(self, tmp_path: Path):
        """Nonexistent skill returns empty list."""
        includes = get_includes(tmp_path / "nonexistent")
        assert includes == []


# =============================================================================
# resolve_includes Tests
# =============================================================================


class TestResolveIncludes:
    """Tests for resolve_includes function."""

    def test_no_includes(self, simple_skill: Path):
        """Skill without includes returns empty list."""
        resolved = resolve_includes(simple_skill)
        assert resolved == []

    def test_single_level_includes(self, composite_skill: Path):
        """Resolves single level includes."""
        resolved = resolve_includes(composite_skill)
        assert len(resolved) == 2

        names = [skill.name for _, skill in resolved]
        assert "component-a" in names
        assert "component-b" in names

    def test_nested_includes(self, nested_composite: Path, composite_skill: Path, component_a: Path, component_b: Path):
        """Resolves nested includes (includes that have their own includes)."""
        resolved = resolve_includes(nested_composite)

        # Should have component-a, component-b, and composite-skill
        names = [skill.name for _, skill in resolved]
        assert len(names) >= 3
        assert "component-a" in names
        assert "component-b" in names
        assert "composite-skill" in names

    def test_circular_dependency_detection(self, circular_a: Path, circular_b: Path):
        """Detects circular dependencies."""
        with pytest.raises(CircularDependencyError):
            resolve_includes(circular_a)

    def test_missing_include_raises_error(self, tmp_path: Path):
        """Missing include raises CompositionError."""
        skill_dir = tmp_path / "broken"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
name: broken
description: Has missing include
includes:
  - ./nonexistent
---

# Broken Skill
""")

        with pytest.raises(CompositionError, match="not found"):
            resolve_includes(skill_dir)


# =============================================================================
# validate_composition Tests
# =============================================================================


class TestValidateComposition:
    """Tests for validate_composition function."""

    def test_valid_composition(self, composite_skill: Path):
        """Valid composition returns no errors."""
        errors = validate_composition(composite_skill)
        assert errors == []

    def test_no_includes(self, simple_skill: Path):
        """Skill without includes returns no errors."""
        errors = validate_composition(simple_skill)
        assert errors == []

    def test_missing_include(self, tmp_path: Path):
        """Missing include returns error."""
        skill_dir = tmp_path / "missing-include"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
name: missing-include
description: Has missing include
includes:
  - ./nonexistent
---

# Missing Include
""")

        errors = validate_composition(skill_dir)
        assert len(errors) == 1
        assert "not found" in errors[0]

    def test_include_not_a_skill(self, tmp_path: Path):
        """Include path exists but is not a skill returns error."""
        skill_dir = tmp_path / "not-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
name: not-skill
description: Includes non-skill directory
includes:
  - ../empty
---

# Not Skill
""")

        # Create empty directory (not a skill)
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        errors = validate_composition(skill_dir)
        assert len(errors) == 1
        assert "not a skill" in errors[0].lower()

    def test_circular_dependency_error(self, circular_a: Path, circular_b: Path):
        """Circular dependency returns error."""
        errors = validate_composition(circular_a)
        assert len(errors) == 1
        assert "circular" in errors[0].lower()


# =============================================================================
# compose_skill Tests
# =============================================================================


class TestComposeSkill:
    """Tests for compose_skill function."""

    def test_skill_without_includes(self, simple_skill: Path):
        """Composing skill without includes returns it as-is."""
        result = compose_skill(simple_skill)

        assert result.success is True
        assert result.skill is not None
        assert result.skill.name == "simple-skill"
        assert result.included_skills == []

    def test_compose_with_includes(self, composite_skill: Path):
        """Composing skill with includes merges content."""
        result = compose_skill(composite_skill)

        assert result.success is True
        assert result.skill is not None
        assert result.skill.name == "composite-skill"
        assert len(result.included_skills) == 2
        assert "component-a" in result.included_skills
        assert "component-b" in result.included_skills

        # Check composed content contains included skills
        assert "## Included: component-a" in result.composed_content
        assert "## Included: component-b" in result.composed_content
        assert "Do thing A." in result.composed_content
        assert "Do thing B." in result.composed_content

    def test_composed_skill_has_no_includes(self, composite_skill: Path):
        """Composed skill does not have includes in frontmatter."""
        result = compose_skill(composite_skill)

        assert result.success is True
        assert result.skill is not None
        assert result.skill.includes == []

        # Check frontmatter doesn't have includes
        assert "includes:" not in result.composed_content.split("---")[1]

    def test_compose_writes_output(self, composite_skill: Path, tmp_path: Path):
        """Compose writes to output path when specified."""
        output_dir = tmp_path / "output"

        result = compose_skill(composite_skill, output_path=output_dir)

        assert result.success is True
        assert output_dir.exists()
        assert (output_dir / "SKILL.md").exists()

        # Verify written content
        written_content = (output_dir / "SKILL.md").read_text()
        assert "## Included: component-a" in written_content

    def test_nonexistent_skill_returns_error(self, tmp_path: Path):
        """Composing nonexistent skill returns error."""
        result = compose_skill(tmp_path / "nonexistent")

        assert result.success is False
        assert result.error is not None
        assert "not found" in result.error.lower()

    def test_compose_with_circular_dependency(self, circular_a: Path, circular_b: Path):
        """Composing skill with circular dependency returns error."""
        result = compose_skill(circular_a)

        assert result.success is False
        assert result.error is not None
        assert "circular" in result.error.lower()

    def test_nested_composition(self, nested_composite: Path, composite_skill: Path, component_a: Path, component_b: Path):
        """Composing nested includes works correctly."""
        result = compose_skill(nested_composite)

        assert result.success is True
        assert result.skill is not None

        # Should have all skills included
        assert "component-a" in result.included_skills
        assert "component-b" in result.included_skills
        assert "composite-skill" in result.included_skills


# =============================================================================
# Skill Model Tests
# =============================================================================


class TestSkillIncludes:
    """Tests for includes field in Skill model."""

    def test_skill_parses_includes(self, composite_skill: Path):
        """Skill parses includes from frontmatter."""
        skill = Skill.from_directory(composite_skill)

        assert len(skill.includes) == 2
        assert "../components/component-a" in skill.includes
        assert "../components/component-b" in skill.includes

    def test_skill_to_skill_md_with_includes(self):
        """Skill generates SKILL.md with includes."""
        skill = Skill(
            name="test-skill",
            description="Test description",
            content="# Test",
            includes=["./component-a", "./component-b"],
        )

        content = skill.to_skill_md()

        assert "includes:" in content
        assert "./component-a" in content
        assert "./component-b" in content

    def test_skill_to_skill_md_without_includes(self):
        """Skill without includes doesn't include field."""
        skill = Skill(
            name="test-skill",
            description="Test description",
            content="# Test",
        )

        content = skill.to_skill_md()

        assert "includes:" not in content


# =============================================================================
# CLI Tests
# =============================================================================


class TestComposeCLI:
    """Tests for compose CLI command."""

    def test_compose_preview(self, composite_skill: Path):
        """CLI compose --preview shows content."""
        result = runner.invoke(app, ["compose", str(composite_skill), "--preview"])

        assert result.exit_code == 0
        assert "Resolved includes" in result.stdout
        assert "component-a" in result.stdout
        assert "component-b" in result.stdout

    def test_compose_writes_output(self, composite_skill: Path, tmp_path: Path):
        """CLI compose writes to output directory."""
        output_dir = tmp_path / "output"

        result = runner.invoke(app, [
            "compose", str(composite_skill),
            "--output", str(output_dir),
        ])

        assert result.exit_code == 0
        assert "Composed skill" in result.stdout
        assert output_dir.exists()
        assert (output_dir / "SKILL.md").exists()

    def test_compose_no_includes(self, simple_skill: Path):
        """CLI compose with no includes shows message."""
        result = runner.invoke(app, ["compose", str(simple_skill)])

        assert result.exit_code == 0
        assert "no includes" in result.stdout.lower()

    def test_compose_nonexistent_skill(self, tmp_path: Path):
        """CLI compose with nonexistent skill shows error."""
        result = runner.invoke(app, ["compose", str(tmp_path / "nonexistent")])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()


class TestValidateCLIWithComposition:
    """Tests for validate CLI with composition features."""

    def test_validate_composite_skill(self, composite_skill: Path):
        """Validate shows includes count for composite skills."""
        result = runner.invoke(app, ["validate", str(composite_skill)])

        assert result.exit_code == 0
        assert "Includes" in result.stdout
        assert "valid" in result.stdout.lower()

    def test_validate_missing_include(self, tmp_path: Path):
        """Validate catches missing includes."""
        skill_dir = tmp_path / "broken"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
name: broken
description: Has missing include
includes:
  - ./nonexistent
---

# Broken Skill
""")

        result = runner.invoke(app, ["validate", str(skill_dir)])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()


class TestPreviewCLIWithComposition:
    """Tests for preview CLI with composition features."""

    def test_preview_composite_skill(self, composite_skill: Path):
        """Preview shows composed version for composite skills."""
        result = runner.invoke(app, ["preview", str(composite_skill)])

        assert result.exit_code == 0
        assert "includes" in result.stdout.lower()
        assert "Included: component-a" in result.stdout
        assert "Included: component-b" in result.stdout


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_single_include(self, tmp_path: Path, component_a: Path):
        """Skill with single include works correctly."""
        skill_dir = tmp_path / "single-include"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
name: single-include
description: Single include
includes:
  - ../components/component-a
---

# Single Include
""")

        result = compose_skill(skill_dir)

        assert result.success is True
        assert len(result.included_skills) == 1
        assert "component-a" in result.included_skills

    def test_include_as_string(self, tmp_path: Path, component_a: Path):
        """Single include as string (not list) works."""
        skill_dir = tmp_path / "string-include"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
name: string-include
description: String include
includes: ../components/component-a
---

# String Include
""")

        result = compose_skill(skill_dir)

        assert result.success is True
        assert len(result.included_skills) == 1

    def test_duplicate_includes_deduplicated(self, tmp_path: Path, component_a: Path):
        """Duplicate includes are deduplicated in output."""
        skill_dir = tmp_path / "duplicate-include"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
name: duplicate-include
description: Duplicate include
includes:
  - ../components/component-a
  - ../components/component-a
---

# Duplicate Include
""")

        result = compose_skill(skill_dir)

        assert result.success is True
        # Should only have one occurrence in composed content
        assert result.composed_content.count("## Included: component-a") == 1

    def test_empty_includes_list(self, tmp_path: Path):
        """Empty includes list is handled correctly."""
        skill_dir = tmp_path / "empty-includes"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
name: empty-includes
description: Empty includes
includes: []
---

# Empty Includes
""")

        assert has_includes(skill_dir) is False
        result = compose_skill(skill_dir)
        assert result.success is True
        assert result.included_skills == []
