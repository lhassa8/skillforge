"""Anthropic Skill model and SKILL.md parsing/generation."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


class SkillError(Exception):
    """Base exception for skill operations."""
    pass


class SkillParseError(SkillError):
    """Raised when SKILL.md parsing fails."""
    pass


class SkillValidationError(SkillError):
    """Raised when skill validation fails."""
    pass


# YAML frontmatter pattern
FRONTMATTER_PATTERN = re.compile(
    r"^---\s*\n(.*?)\n---\s*\n(.*)$",
    re.DOTALL
)

# Validation constraints from Anthropic docs
MAX_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024
NAME_PATTERN = re.compile(r"^[a-z0-9-]+$")
RESERVED_WORDS = {"anthropic", "claude"}
XML_TAG_PATTERN = re.compile(r"<[^>]+>")


@dataclass
class Skill:
    """Represents an Anthropic Agent Skill."""

    name: str
    description: str
    content: str = ""
    path: Optional[Path] = None

    # Additional files in the skill directory
    additional_files: list[str] = field(default_factory=list)
    scripts: list[str] = field(default_factory=list)

    def to_skill_md(self) -> str:
        """Generate SKILL.md content."""
        frontmatter = yaml.dump(
            {"name": self.name, "description": self.description},
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        ).strip()

        return f"---\n{frontmatter}\n---\n\n{self.content}"

    @classmethod
    def from_skill_md(cls, content: str, path: Optional[Path] = None) -> Skill:
        """Parse a SKILL.md file content.

        Args:
            content: The SKILL.md file content
            path: Optional path to the skill directory

        Returns:
            Skill instance

        Raises:
            SkillParseError: If parsing fails
        """
        match = FRONTMATTER_PATTERN.match(content)
        if not match:
            raise SkillParseError(
                "Invalid SKILL.md format. Expected YAML frontmatter between --- markers."
            )

        frontmatter_str = match.group(1)
        body = match.group(2).strip()

        try:
            frontmatter = yaml.safe_load(frontmatter_str)
        except yaml.YAMLError as e:
            raise SkillParseError(f"Invalid YAML frontmatter: {e}")

        if not isinstance(frontmatter, dict):
            raise SkillParseError("Frontmatter must be a YAML dictionary")

        name = frontmatter.get("name")
        description = frontmatter.get("description")

        if not name:
            raise SkillParseError("Missing required field: name")
        if not description:
            raise SkillParseError("Missing required field: description")

        skill = cls(
            name=name,
            description=description,
            content=body,
            path=path,
        )

        # Discover additional files if path is provided
        if path and path.is_dir():
            skill._discover_files()

        return skill

    @classmethod
    def from_directory(cls, skill_dir: Path) -> Skill:
        """Load a skill from a directory.

        Args:
            skill_dir: Path to the skill directory

        Returns:
            Skill instance

        Raises:
            SkillParseError: If SKILL.md is missing or invalid
        """
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            raise SkillParseError(f"SKILL.md not found in {skill_dir}")

        content = skill_md.read_text()
        return cls.from_skill_md(content, skill_dir)

    def _discover_files(self) -> None:
        """Discover additional markdown files and scripts."""
        if not self.path:
            return

        # Find additional markdown files
        for md_file in self.path.glob("*.md"):
            if md_file.name != "SKILL.md":
                self.additional_files.append(md_file.name)

        # Find scripts
        scripts_dir = self.path / "scripts"
        if scripts_dir.is_dir():
            for script in scripts_dir.iterdir():
                if script.is_file():
                    self.scripts.append(script.name)

    def validate(self) -> list[str]:
        """Validate the skill against Anthropic requirements.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Validate name
        if not self.name:
            errors.append("Name is required")
        elif len(self.name) > MAX_NAME_LENGTH:
            errors.append(f"Name exceeds {MAX_NAME_LENGTH} characters")
        elif not NAME_PATTERN.match(self.name):
            errors.append("Name must contain only lowercase letters, numbers, and hyphens")
        elif any(word in self.name for word in RESERVED_WORDS):
            errors.append("Name cannot contain reserved words: 'anthropic', 'claude'")
        if self.name and XML_TAG_PATTERN.search(self.name):
            errors.append("Name cannot contain XML tags")

        # Validate description
        if not self.description:
            errors.append("Description is required")
        elif len(self.description) > MAX_DESCRIPTION_LENGTH:
            errors.append(f"Description exceeds {MAX_DESCRIPTION_LENGTH} characters")
        if self.description and XML_TAG_PATTERN.search(self.description):
            errors.append("Description cannot contain XML tags")

        return errors

    def is_valid(self) -> bool:
        """Check if the skill is valid."""
        return len(self.validate()) == 0


def generate_skill_content(name: str, description: str = "") -> str:
    """Generate default SKILL.md body content.

    Args:
        name: Skill name
        description: Optional description

    Returns:
        Markdown content for the skill body
    """
    title = name.replace("-", " ").title()

    return f"""# {title}

## Overview

{description or "TODO: Describe what this skill does and when Claude should use it."}

## Instructions

<!--
Provide clear, step-by-step guidance for Claude to follow.
Be specific about:
- When to use this skill
- What steps to take
- What output to produce
- Edge cases to handle
-->

1. First, understand what the user is trying to accomplish
2. Then, [describe the main action]
3. Finally, [describe the expected outcome]

## Examples

### Example 1: [Describe scenario]

**User request:** "[Example user message]"

**What to do:**
1. [Step 1]
2. [Step 2]

### Example 2: [Describe another scenario]

**User request:** "[Example user message]"

**What to do:**
1. [Step 1]
2. [Step 2]

## Additional Resources

<!--
Reference additional files in this skill directory if needed.
Claude will read these files when necessary.

For example:
- See [REFERENCE.md](REFERENCE.md) for detailed API documentation
- See [scripts/helper.py](scripts/helper.py) for utility functions
-->

## Notes

- This skill was created with SkillForge
- Modify the instructions above to match your use case
"""


def normalize_skill_name(name: str) -> str:
    """Normalize a skill name to meet Anthropic requirements.

    Args:
        name: Raw skill name

    Returns:
        Normalized name (lowercase, hyphens, no special chars)
    """
    # Convert to lowercase
    name = name.lower()

    # Replace spaces and underscores with hyphens
    name = re.sub(r"[\s_]+", "-", name)

    # Remove any character that's not alphanumeric or hyphen
    name = re.sub(r"[^a-z0-9-]", "", name)

    # Collapse multiple hyphens
    name = re.sub(r"-+", "-", name)

    # Remove leading/trailing hyphens
    name = name.strip("-")

    # Truncate to max length
    if len(name) > MAX_NAME_LENGTH:
        name = name[:MAX_NAME_LENGTH].rstrip("-")

    return name
