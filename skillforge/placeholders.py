"""Placeholder substitution for SkillForge skills."""

import re
from typing import Any, Optional


class PlaceholderError(Exception):
    """Raised when placeholder substitution fails."""

    pass


# Pattern to match placeholders like {name} or {target_dir}
PLACEHOLDER_PATTERN = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")

# Pattern to match secret placeholders like {secret:name}
SECRET_PLACEHOLDER_PATTERN = re.compile(r"\{secret:([a-zA-Z_][a-zA-Z0-9_]*)\}")


def substitute(
    template: str,
    context: dict[str, Any],
    secret_manager: Optional[Any] = None,
) -> str:
    """Substitute placeholders in a template string.

    Args:
        template: String containing {placeholder} or {secret:name} patterns
        context: Dictionary of placeholder names to values
        secret_manager: Optional SecretManager for resolving {secret:name} placeholders

    Returns:
        String with placeholders replaced by values

    Raises:
        PlaceholderError: If a placeholder is not found in context
    """
    result = template

    # First, resolve secret placeholders if secret_manager is provided
    if secret_manager is not None:
        def replace_secret(match: re.Match) -> str:
            name = match.group(1)
            try:
                return secret_manager.get(name)
            except Exception as e:
                raise PlaceholderError(f"Secret not found: {name} ({e})")

        result = SECRET_PLACEHOLDER_PATTERN.sub(replace_secret, result)

    # Then, resolve regular placeholders
    def replace(match: re.Match) -> str:
        name = match.group(1)
        if name not in context:
            raise PlaceholderError(f"Unknown placeholder: {{{name}}}")
        value = context[name]
        return str(value) if value is not None else ""

    return PLACEHOLDER_PATTERN.sub(replace, result)


def substitute_dict(
    data: dict[str, Any],
    context: dict[str, Any],
    secret_manager: Optional[Any] = None,
) -> dict[str, Any]:
    """Recursively substitute placeholders in a dictionary.

    Args:
        data: Dictionary that may contain placeholder strings
        context: Dictionary of placeholder names to values
        secret_manager: Optional SecretManager for resolving {secret:name} placeholders

    Returns:
        New dictionary with placeholders substituted
    """
    result = {}
    for key, value in data.items():
        result[key] = substitute_value(value, context, secret_manager)
    return result


def substitute_value(
    value: Any,
    context: dict[str, Any],
    secret_manager: Optional[Any] = None,
) -> Any:
    """Substitute placeholders in any value type.

    Args:
        value: Value that may contain placeholders (str, dict, list, or other)
        context: Dictionary of placeholder names to values
        secret_manager: Optional SecretManager for resolving {secret:name} placeholders

    Returns:
        Value with placeholders substituted
    """
    if isinstance(value, str):
        return substitute(value, context, secret_manager)
    elif isinstance(value, dict):
        return substitute_dict(value, context, secret_manager)
    elif isinstance(value, list):
        return [substitute_value(item, context, secret_manager) for item in value]
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


def extract_secret_placeholders(template: str) -> list[str]:
    """Extract all secret placeholder names from a template string.

    Args:
        template: String containing {secret:name} patterns

    Returns:
        List of secret names found
    """
    return SECRET_PLACEHOLDER_PATTERN.findall(template)


def has_secret_placeholders(template: str) -> bool:
    """Check if a template contains any secret placeholders.

    Args:
        template: String that may contain {secret:name} patterns

    Returns:
        True if the template contains secret placeholders
    """
    return bool(SECRET_PLACEHOLDER_PATTERN.search(template))
