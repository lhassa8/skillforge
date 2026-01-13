"""Placeholder substitution for SkillForge skills."""

import re
from typing import Any


class PlaceholderError(Exception):
    """Raised when placeholder substitution fails."""

    pass


# Pattern to match placeholders like {name} or {target_dir}
PLACEHOLDER_PATTERN = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


def substitute(template: str, context: dict[str, Any]) -> str:
    """Substitute placeholders in a template string.

    Args:
        template: String containing {placeholder} patterns
        context: Dictionary of placeholder names to values

    Returns:
        String with placeholders replaced by values

    Raises:
        PlaceholderError: If a placeholder is not found in context
    """
    def replace(match: re.Match) -> str:
        name = match.group(1)
        if name not in context:
            raise PlaceholderError(f"Unknown placeholder: {{{name}}}")
        value = context[name]
        return str(value) if value is not None else ""

    return PLACEHOLDER_PATTERN.sub(replace, template)


def substitute_dict(data: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Recursively substitute placeholders in a dictionary.

    Args:
        data: Dictionary that may contain placeholder strings
        context: Dictionary of placeholder names to values

    Returns:
        New dictionary with placeholders substituted
    """
    result = {}
    for key, value in data.items():
        result[key] = substitute_value(value, context)
    return result


def substitute_value(value: Any, context: dict[str, Any]) -> Any:
    """Substitute placeholders in any value type.

    Args:
        value: Value that may contain placeholders (str, dict, list, or other)
        context: Dictionary of placeholder names to values

    Returns:
        Value with placeholders substituted
    """
    if isinstance(value, str):
        return substitute(value, context)
    elif isinstance(value, dict):
        return substitute_dict(value, context)
    elif isinstance(value, list):
        return [substitute_value(item, context) for item in value]
    else:
        return value


def build_context(
    target_dir: str,
    sandbox_dir: str,
    inputs: dict[str, Any],
) -> dict[str, Any]:
    """Build the placeholder context for skill execution.

    Args:
        target_dir: Original target directory path
        sandbox_dir: Sandbox directory path (where execution happens)
        inputs: Resolved input values

    Returns:
        Context dictionary for placeholder substitution
    """
    context = {
        "target_dir": sandbox_dir,  # Steps run in sandbox
        "sandbox_dir": sandbox_dir,
        "original_target_dir": target_dir,
    }
    # Add all inputs to context
    context.update(inputs)
    return context


def extract_placeholders(template: str) -> list[str]:
    """Extract all placeholder names from a template string.

    Args:
        template: String containing {placeholder} patterns

    Returns:
        List of placeholder names found
    """
    return PLACEHOLDER_PATTERN.findall(template)
