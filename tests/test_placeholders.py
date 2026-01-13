"""Tests for placeholder substitution."""

import pytest

from skillforge.placeholders import (
    substitute,
    substitute_dict,
    substitute_value,
    build_context,
    extract_placeholders,
    PlaceholderError,
)


class TestSubstitute:
    """Tests for string substitution."""

    def test_simple_substitution(self):
        """Test basic placeholder substitution."""
        result = substitute("Hello {name}!", {"name": "World"})
        assert result == "Hello World!"

    def test_multiple_placeholders(self):
        """Test multiple placeholders in one string."""
        result = substitute("{greeting} {name}!", {"greeting": "Hi", "name": "User"})
        assert result == "Hi User!"

    def test_no_placeholders(self):
        """Test string without placeholders."""
        result = substitute("Hello World!", {})
        assert result == "Hello World!"

    def test_missing_placeholder_raises(self):
        """Test that missing placeholder raises error."""
        with pytest.raises(PlaceholderError) as exc_info:
            substitute("Hello {unknown}!", {})
        assert "unknown" in str(exc_info.value)

    def test_path_placeholder(self):
        """Test path-like placeholder."""
        result = substitute("{target_dir}/file.txt", {"target_dir": "/tmp/test"})
        assert result == "/tmp/test/file.txt"

    def test_none_value(self):
        """Test None value becomes empty string."""
        result = substitute("Value: {value}", {"value": None})
        assert result == "Value: "


class TestSubstituteDict:
    """Tests for dictionary substitution."""

    def test_substitutes_string_values(self):
        """Test substitution in dictionary string values."""
        data = {"path": "{target_dir}/file.txt", "name": "test"}
        result = substitute_dict(data, {"target_dir": "/tmp"})

        assert result["path"] == "/tmp/file.txt"
        assert result["name"] == "test"

    def test_preserves_non_string_values(self):
        """Test that non-string values are preserved."""
        data = {"count": 42, "enabled": True, "value": None}
        result = substitute_dict(data, {})

        assert result["count"] == 42
        assert result["enabled"] is True
        assert result["value"] is None


class TestSubstituteValue:
    """Tests for value substitution."""

    def test_string_value(self):
        """Test string value substitution."""
        result = substitute_value("{name}", {"name": "test"})
        assert result == "test"

    def test_list_value(self):
        """Test list value substitution."""
        result = substitute_value(["{a}", "{b}"], {"a": "1", "b": "2"})
        assert result == ["1", "2"]

    def test_nested_dict(self):
        """Test nested dictionary substitution."""
        data = {"outer": {"inner": "{value}"}}
        result = substitute_value(data, {"value": "test"})
        assert result["outer"]["inner"] == "test"

    def test_mixed_list(self):
        """Test list with mixed types."""
        data = ["{name}", 42, {"key": "{value}"}]
        result = substitute_value(data, {"name": "test", "value": "val"})
        assert result == ["test", 42, {"key": "val"}]


class TestBuildContext:
    """Tests for context building."""

    def test_includes_builtins(self):
        """Test that built-in placeholders are included."""
        context = build_context("/target", "/sandbox", {})

        assert context["target_dir"] == "/sandbox"
        assert context["sandbox_dir"] == "/sandbox"
        assert context["original_target_dir"] == "/target"

    def test_includes_inputs(self):
        """Test that inputs are included."""
        inputs = {"version": "1.0.0", "name": "test"}
        context = build_context("/target", "/sandbox", inputs)

        assert context["version"] == "1.0.0"
        assert context["name"] == "test"


class TestExtractPlaceholders:
    """Tests for placeholder extraction."""

    def test_extracts_placeholders(self):
        """Test extraction of placeholder names."""
        result = extract_placeholders("{a} and {b} and {c}")
        assert set(result) == {"a", "b", "c"}

    def test_no_placeholders(self):
        """Test string without placeholders."""
        result = extract_placeholders("no placeholders here")
        assert result == []

    def test_duplicate_placeholders(self):
        """Test that duplicates are included."""
        result = extract_placeholders("{a} and {a}")
        assert result == ["a", "a"]
