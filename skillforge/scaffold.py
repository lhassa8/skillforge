"""Scaffold generator for Anthropic Agent Skills."""

from pathlib import Path
from typing import Optional

from skillforge.skill import (
    Skill,
    generate_skill_content,
    normalize_skill_name,
)


def create_skill_scaffold(
    name: str,
    output_dir: Path,
    description: str = "",
    with_scripts: bool = False,
    force: bool = False,
) -> Path:
    """Create a new Anthropic Skill scaffold.

    Args:
        name: Name of the skill (will be normalized)
        output_dir: Parent directory for the skill folder
        description: Optional description for the skill
        with_scripts: If True, create a scripts/ directory with example
        force: If True, overwrite existing skill folder

    Returns:
        Path to the created skill directory

    Raises:
        FileExistsError: If skill directory already exists and force is False
    """
    # Normalize the skill name
    safe_name = normalize_skill_name(name)

    if not safe_name:
        raise ValueError(f"Invalid skill name: {name}")

    skill_dir = output_dir / safe_name

    if skill_dir.exists() and not force:
        raise FileExistsError(f"Skill directory already exists: {skill_dir}")

    # Create directory structure
    skill_dir.mkdir(parents=True, exist_ok=True)

    # Generate default description if not provided
    if not description:
        description = f"TODO: Describe what {safe_name} does and when Claude should use it."

    # Generate SKILL.md content
    content = generate_skill_content(safe_name, description)

    skill = Skill(
        name=safe_name,
        description=description,
        content=content,
        path=skill_dir,
    )

    # Write SKILL.md
    skill_md_path = skill_dir / "SKILL.md"
    skill_md_path.write_text(skill.to_skill_md())

    # Create scripts directory if requested
    if with_scripts:
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(exist_ok=True)

        # Create example script
        example_script = scripts_dir / "example.py"
        example_script.write_text(generate_example_script(safe_name))

    return skill_dir


def generate_example_script(skill_name: str) -> str:
    """Generate an example Python script for a skill.

    Args:
        skill_name: Name of the skill

    Returns:
        Python script content
    """
    return f'''#!/usr/bin/env python3
"""Example utility script for {skill_name} skill.

This script can be executed by Claude when using this skill.
The output will be returned to Claude (the script code itself
is not loaded into context).

Usage:
    python scripts/example.py [args]
"""

import sys
import json


def main():
    """Main function."""
    # Example: Process input and return structured output
    result = {{
        "status": "success",
        "message": "Example script executed successfully",
        "skill": "{skill_name}",
    }}

    # Output JSON for easy parsing
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
'''


def generate_reference_doc(skill_name: str, topic: str = "Reference") -> str:
    """Generate a reference document template.

    Args:
        skill_name: Name of the skill
        topic: Topic for the reference document

    Returns:
        Markdown content
    """
    return f"""# {topic}

This document provides additional reference information for the {skill_name} skill.

## Overview

<!-- Add detailed documentation here -->

## API Reference

<!-- If this skill interacts with an API, document it here -->

## Examples

<!-- Add detailed examples here -->

## Troubleshooting

<!-- Add common issues and solutions here -->
"""


def add_reference_doc(
    skill_dir: Path,
    filename: str,
    content: Optional[str] = None,
) -> Path:
    """Add a reference document to a skill.

    Args:
        skill_dir: Path to the skill directory
        filename: Name for the markdown file (e.g., "REFERENCE.md")
        content: Optional content (generates template if not provided)

    Returns:
        Path to the created file
    """
    if not filename.endswith(".md"):
        filename = f"{filename}.md"

    # Get skill name for template
    skill_name = skill_dir.name

    if content is None:
        topic = filename.replace(".md", "").replace("-", " ").replace("_", " ").title()
        content = generate_reference_doc(skill_name, topic)

    file_path = skill_dir / filename
    file_path.write_text(content)

    return file_path


def add_script(
    skill_dir: Path,
    filename: str,
    content: Optional[str] = None,
    language: str = "python",
) -> Path:
    """Add a script to a skill.

    Args:
        skill_dir: Path to the skill directory
        filename: Name for the script file
        content: Optional content (generates template if not provided)
        language: Script language ("python", "bash", "node")

    Returns:
        Path to the created file
    """
    scripts_dir = skill_dir / "scripts"
    scripts_dir.mkdir(exist_ok=True)

    # Ensure correct extension
    ext_map = {
        "python": ".py",
        "bash": ".sh",
        "node": ".js",
        "javascript": ".js",
    }
    expected_ext = ext_map.get(language, "")
    if expected_ext and not filename.endswith(expected_ext):
        filename = f"{filename}{expected_ext}"

    if content is None:
        content = _generate_script_template(skill_dir.name, language)

    file_path = scripts_dir / filename
    file_path.write_text(content)

    # Make executable on Unix
    try:
        file_path.chmod(0o755)
    except OSError:
        pass  # Windows doesn't support chmod

    return file_path


def _generate_script_template(skill_name: str, language: str) -> str:
    """Generate a script template."""
    if language == "python":
        return generate_example_script(skill_name)

    elif language in ("bash", "sh"):
        return f"""#!/bin/bash
# Utility script for {skill_name} skill

set -euo pipefail

echo "Script executed successfully"
"""

    elif language in ("node", "javascript"):
        return f"""#!/usr/bin/env node
/**
 * Utility script for {skill_name} skill
 */

console.log(JSON.stringify({{
    status: "success",
    message: "Script executed successfully",
    skill: "{skill_name}"
}}, null, 2));
"""

    else:
        return f"# Script for {skill_name}\n"
