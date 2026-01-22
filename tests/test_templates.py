"""Tests for skill templates functionality."""

import pytest
from pathlib import Path
from typer.testing import CliRunner

from skillforge.templates import (
    SkillTemplate,
    get_template,
    list_templates,
    get_templates_by_category,
    get_template_names,
    BUILTIN_TEMPLATES,
)
from skillforge.scaffold import create_skill_scaffold
from skillforge.cli import app


runner = CliRunner()


# =============================================================================
# SkillTemplate Tests
# =============================================================================


class TestSkillTemplate:
    """Tests for SkillTemplate dataclass."""

    def test_template_has_required_fields(self):
        """Template should have all required fields."""
        template = SkillTemplate(
            name="test-template",
            title="Test Template",
            description="A test template",
            category="Testing",
            content="# Test content",
            tags=["test"],
        )
        assert template.name == "test-template"
        assert template.title == "Test Template"
        assert template.description == "A test template"
        assert template.category == "Testing"
        assert template.content == "# Test content"
        assert template.tags == ["test"]

    def test_template_default_tags(self):
        """Template should have empty tags by default."""
        template = SkillTemplate(
            name="test",
            title="Test",
            description="Test",
            category="Test",
            content="Content",
        )
        assert template.tags == []


# =============================================================================
# Built-in Templates Tests
# =============================================================================


class TestBuiltinTemplates:
    """Tests for built-in templates."""

    def test_all_builtin_templates_exist(self):
        """All expected templates should exist."""
        expected_templates = [
            "code-review",
            "git-commit",
            "git-pr",
            "api-docs",
            "debugging",
            "sql-helper",
            "test-writer",
            "explainer",
        ]
        for name in expected_templates:
            assert name in BUILTIN_TEMPLATES, f"Missing template: {name}"

    def test_builtin_templates_have_content(self):
        """All templates should have non-empty content."""
        for name, template in BUILTIN_TEMPLATES.items():
            assert template.content, f"Template {name} has no content"
            assert len(template.content) > 100, f"Template {name} content too short"

    def test_builtin_templates_have_valid_fields(self):
        """All templates should have valid required fields."""
        for name, template in BUILTIN_TEMPLATES.items():
            assert template.name == name, f"Template {name} name mismatch"
            assert template.title, f"Template {name} has no title"
            assert template.description, f"Template {name} has no description"
            assert template.category, f"Template {name} has no category"
            assert isinstance(template.tags, list), f"Template {name} tags not a list"

    def test_code_review_template_content(self):
        """Code review template should have key sections."""
        template = BUILTIN_TEMPLATES["code-review"]
        assert "Review Checklist" in template.content
        assert "Correctness" in template.content
        assert "Security" in template.content
        assert "Performance" in template.content

    def test_git_commit_template_content(self):
        """Git commit template should have conventional commit types."""
        template = BUILTIN_TEMPLATES["git-commit"]
        assert "feat" in template.content
        assert "fix" in template.content
        assert "docs" in template.content
        assert "refactor" in template.content


# =============================================================================
# Template API Tests
# =============================================================================


class TestGetTemplate:
    """Tests for get_template function."""

    def test_get_existing_template(self):
        """Should return template for valid name."""
        template = get_template("code-review")
        assert template is not None
        assert template.name == "code-review"

    def test_get_nonexistent_template(self):
        """Should return None for invalid name."""
        template = get_template("nonexistent")
        assert template is None

    def test_get_template_case_sensitive(self):
        """Template lookup should be case-sensitive."""
        assert get_template("code-review") is not None
        assert get_template("CODE-REVIEW") is None
        assert get_template("Code-Review") is None


class TestListTemplates:
    """Tests for list_templates function."""

    def test_returns_all_templates(self):
        """Should return all built-in templates."""
        templates = list_templates()
        assert len(templates) == len(BUILTIN_TEMPLATES)

    def test_templates_sorted_by_category_then_name(self):
        """Templates should be sorted by category, then name."""
        templates = list_templates()
        # Check sorting
        for i in range(len(templates) - 1):
            curr = templates[i]
            next_tmpl = templates[i + 1]
            assert (curr.category, curr.name) <= (next_tmpl.category, next_tmpl.name)


class TestGetTemplatesByCategory:
    """Tests for get_templates_by_category function."""

    def test_returns_dict_of_categories(self):
        """Should return dict mapping categories to templates."""
        by_category = get_templates_by_category()
        assert isinstance(by_category, dict)
        assert len(by_category) > 0

    def test_all_templates_in_categories(self):
        """All templates should be in a category."""
        by_category = get_templates_by_category()
        total = sum(len(templates) for templates in by_category.values())
        assert total == len(BUILTIN_TEMPLATES)

    def test_expected_categories_exist(self):
        """Expected categories should exist."""
        by_category = get_templates_by_category()
        # At minimum, we expect these categories
        assert "Code Quality" in by_category
        assert "Git" in by_category
        assert "Documentation" in by_category


class TestGetTemplateNames:
    """Tests for get_template_names function."""

    def test_returns_sorted_list(self):
        """Should return sorted list of template names."""
        names = get_template_names()
        assert names == sorted(names)

    def test_returns_all_names(self):
        """Should return all template names."""
        names = get_template_names()
        assert len(names) == len(BUILTIN_TEMPLATES)
        for name in names:
            assert name in BUILTIN_TEMPLATES


# =============================================================================
# Scaffold with Template Tests
# =============================================================================


class TestCreateSkillScaffoldWithTemplate:
    """Tests for create_skill_scaffold with templates."""

    def test_create_skill_with_template(self, tmp_path: Path):
        """Should create skill from template."""
        skill_dir, used_template = create_skill_scaffold(
            name="my-reviewer",
            output_dir=tmp_path,
            template="code-review",
        )

        assert skill_dir.exists()
        assert used_template is not None
        assert used_template.name == "code-review"

        # Check SKILL.md content
        skill_md = skill_dir / "SKILL.md"
        assert skill_md.exists()
        content = skill_md.read_text()
        assert "my-reviewer" in content
        assert "Review Checklist" in content

    def test_create_skill_with_custom_description(self, tmp_path: Path):
        """Custom description should override template description."""
        skill_dir, used_template = create_skill_scaffold(
            name="custom-reviewer",
            output_dir=tmp_path,
            description="My custom description",
            template="code-review",
        )

        skill_md = skill_dir / "SKILL.md"
        content = skill_md.read_text()
        assert "My custom description" in content

    def test_create_skill_without_template(self, tmp_path: Path):
        """Should work without template (backward compatible)."""
        skill_dir, used_template = create_skill_scaffold(
            name="plain-skill",
            output_dir=tmp_path,
        )

        assert skill_dir.exists()
        assert used_template is None

    def test_invalid_template_raises_error(self, tmp_path: Path):
        """Should raise ValueError for invalid template."""
        with pytest.raises(ValueError) as exc_info:
            create_skill_scaffold(
                name="test-skill",
                output_dir=tmp_path,
                template="nonexistent-template",
            )
        assert "Unknown template" in str(exc_info.value)
        assert "nonexistent-template" in str(exc_info.value)


# =============================================================================
# CLI Tests
# =============================================================================


class TestTemplatesCLI:
    """Tests for templates CLI commands."""

    def test_templates_list(self):
        """'skillforge templates' should list templates."""
        result = runner.invoke(app, ["templates"])
        assert result.exit_code == 0
        assert "Available Templates" in result.stdout
        assert "code-review" in result.stdout
        assert "git-commit" in result.stdout

    def test_templates_show_valid(self):
        """'skillforge templates show' should show template details."""
        result = runner.invoke(app, ["templates", "show", "code-review"])
        assert result.exit_code == 0
        assert "code-review" in result.stdout
        assert "Code Quality" in result.stdout
        assert "Review Checklist" in result.stdout

    def test_templates_show_invalid(self):
        """'skillforge templates show' with invalid name should error."""
        result = runner.invoke(app, ["templates", "show", "nonexistent"])
        assert result.exit_code == 1
        assert "Unknown template" in result.stdout

    def test_new_with_template(self, tmp_path: Path):
        """'skillforge new --template' should create skill from template."""
        result = runner.invoke(
            app,
            ["new", "my-skill", "--template", "code-review", "--out", str(tmp_path)],
        )
        assert result.exit_code == 0
        assert "Created skill" in result.stdout
        assert "code-review" in result.stdout

        # Check skill was created
        skill_dir = tmp_path / "my-skill"
        assert skill_dir.exists()

    def test_new_with_invalid_template(self, tmp_path: Path):
        """'skillforge new --template' with invalid template should error."""
        result = runner.invoke(
            app,
            ["new", "my-skill", "--template", "nonexistent", "--out", str(tmp_path)],
        )
        assert result.exit_code == 1
        assert "Unknown template" in result.stdout
