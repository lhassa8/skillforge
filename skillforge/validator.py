"""Validation for Anthropic Agent Skills."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from skillforge.skill import (
    Skill,
    SkillParseError,
    MAX_NAME_LENGTH,
    MAX_DESCRIPTION_LENGTH,
    NAME_PATTERN,
    RESERVED_WORDS,
    XML_TAG_PATTERN,
)


@dataclass
class ValidationMessage:
    """A validation message (error or warning)."""

    level: str  # "error" or "warning"
    message: str
    location: Optional[str] = None

    def __str__(self) -> str:
        """Format the validation message for display.

        Returns:
            Formatted string like "[ERROR] location: message" or "[WARNING] message"
        """
        if self.location:
            return f"[{self.level.upper()}] {self.location}: {self.message}"
        return f"[{self.level.upper()}] {self.message}"


@dataclass
class ValidationResult:
    """Result of skill validation."""

    valid: bool = True
    messages: list[ValidationMessage] = field(default_factory=list)
    skill: Optional[Skill] = None

    def add_error(self, message: str, location: Optional[str] = None) -> None:
        """Add an error message."""
        self.valid = False
        self.messages.append(ValidationMessage("error", message, location))

    def add_warning(self, message: str, location: Optional[str] = None) -> None:
        """Add a warning message."""
        self.messages.append(ValidationMessage("warning", message, location))

    @property
    def errors(self) -> list[ValidationMessage]:
        """Get only error messages."""
        return [m for m in self.messages if m.level == "error"]

    @property
    def warnings(self) -> list[ValidationMessage]:
        """Get only warning messages."""
        return [m for m in self.messages if m.level == "warning"]


def validate_skill_directory(skill_dir: Path) -> ValidationResult:
    """Validate a skill directory.

    Args:
        skill_dir: Path to the skill directory

    Returns:
        ValidationResult with all validation messages
    """
    result = ValidationResult()

    # Check directory exists
    if not skill_dir.exists():
        result.add_error(f"Directory does not exist: {skill_dir}")
        return result

    if not skill_dir.is_dir():
        result.add_error(f"Not a directory: {skill_dir}")
        return result

    # Check SKILL.md exists
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        result.add_error("SKILL.md not found", "SKILL.md")
        return result

    # Parse and validate SKILL.md
    try:
        skill = Skill.from_directory(skill_dir)
        result.skill = skill
    except SkillParseError as e:
        result.add_error(str(e), "SKILL.md")
        return result

    # Run skill validation
    validation_errors = skill.validate()
    for error in validation_errors:
        result.add_error(error, "SKILL.md frontmatter")

    # Check for common issues
    _check_content_quality(skill, result)
    _check_file_structure(skill_dir, result)

    return result


def validate_skill_md(content: str) -> ValidationResult:
    """Validate SKILL.md content directly.

    Args:
        content: The SKILL.md file content

    Returns:
        ValidationResult with all validation messages
    """
    result = ValidationResult()

    try:
        skill = Skill.from_skill_md(content)
        result.skill = skill
    except SkillParseError as e:
        result.add_error(str(e), "SKILL.md")
        return result

    # Run skill validation
    validation_errors = skill.validate()
    for error in validation_errors:
        result.add_error(error, "frontmatter")

    # Check content quality
    _check_content_quality(skill, result)

    return result


def _check_content_quality(skill: Skill, result: ValidationResult) -> None:
    """Check for content quality issues."""

    # Check for empty or minimal content
    if len(skill.content.strip()) < 50:
        result.add_warning(
            "Skill content is very short. Consider adding more detailed instructions.",
            "content"
        )

    # Check for TODO markers
    if "TODO" in skill.content:
        result.add_warning(
            "Content contains TODO markers that should be completed.",
            "content"
        )

    # Check for placeholder text
    placeholder_patterns = [
        "[describe",
        "[example",
        "[step",
        "[your",
    ]
    for pattern in placeholder_patterns:
        if pattern.lower() in skill.content.lower():
            result.add_warning(
                f"Content may contain placeholder text: '{pattern}...'",
                "content"
            )
            break

    # Check description mentions when to use the skill
    trigger_words = ["when", "use when", "trigger", "if the user", "whenever"]
    if not any(word in skill.description.lower() for word in trigger_words):
        result.add_warning(
            "Description should explain when Claude should use this skill. "
            "Consider adding trigger conditions like 'Use when...'",
            "description"
        )


def _check_file_structure(skill_dir: Path, result: ValidationResult) -> None:
    """Check file structure for issues."""

    # Check for common misnamed files
    for item in skill_dir.iterdir():
        if item.is_file():
            name_lower = item.name.lower()

            # Check for wrong casing
            if name_lower == "skill.md" and item.name != "SKILL.md":
                result.add_error(
                    f"Found '{item.name}' but it should be 'SKILL.md' (uppercase)",
                    item.name
                )

            # Check for alternative extensions
            if name_lower.endswith(".markdown"):
                result.add_warning(
                    f"Consider using .md extension instead of .markdown: {item.name}",
                    item.name
                )

    # Check scripts directory
    scripts_dir = skill_dir / "scripts"
    if scripts_dir.exists():
        if not scripts_dir.is_dir():
            result.add_error("'scripts' exists but is not a directory", "scripts")
        else:
            # Check for executable scripts
            for script in scripts_dir.iterdir():
                if script.is_file():
                    # Check for shebang in shell scripts
                    if script.suffix in (".sh", ".bash"):
                        content = script.read_text()
                        if not content.startswith("#!"):
                            result.add_warning(
                                f"Shell script missing shebang: {script.name}",
                                f"scripts/{script.name}"
                            )


def validate_name(name: str) -> list[str]:
    """Validate a skill name.

    Args:
        name: The skill name to validate

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    if not name:
        errors.append("Name is required")
        return errors

    if len(name) > MAX_NAME_LENGTH:
        errors.append(f"Name exceeds {MAX_NAME_LENGTH} characters")

    if not NAME_PATTERN.match(name):
        errors.append("Name must contain only lowercase letters, numbers, and hyphens")

    if any(word in name for word in RESERVED_WORDS):
        errors.append("Name cannot contain reserved words: 'anthropic', 'claude'")

    if XML_TAG_PATTERN.search(name):
        errors.append("Name cannot contain XML tags")

    return errors


def validate_description(description: str) -> list[str]:
    """Validate a skill description.

    Args:
        description: The skill description to validate

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    if not description:
        errors.append("Description is required")
        return errors

    if len(description) > MAX_DESCRIPTION_LENGTH:
        errors.append(f"Description exceeds {MAX_DESCRIPTION_LENGTH} characters")

    if XML_TAG_PATTERN.search(description):
        errors.append("Description cannot contain XML tags")

    return errors
