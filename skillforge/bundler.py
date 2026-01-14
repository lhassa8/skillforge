"""Bundle Anthropic Skills for distribution."""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Generator

# Maximum bundle size before warning (10MB)
MAX_BUNDLE_SIZE = 10 * 1024 * 1024

from skillforge.skill import Skill, SkillParseError
from skillforge.validator import validate_skill_directory, ValidationResult


@dataclass
class BundleResult:
    """Result of bundling a skill."""

    success: bool
    output_path: Optional[Path] = None
    skill_name: Optional[str] = None
    file_count: int = 0
    total_size: int = 0
    validation: Optional[ValidationResult] = None
    error_message: Optional[str] = None


def bundle_skill(
    skill_dir: Path,
    output_path: Optional[Path] = None,
    validate: bool = True,
    include_hidden: bool = False,
) -> BundleResult:
    """Bundle a skill directory into a zip file for upload.

    Args:
        skill_dir: Path to the skill directory
        output_path: Optional output path for the zip file
        validate: If True, validate the skill before bundling
        include_hidden: If True, include hidden files (starting with .)

    Returns:
        BundleResult with bundling outcome
    """
    result = BundleResult(success=False)

    # Validate first if requested
    if validate:
        validation = validate_skill_directory(skill_dir)
        result.validation = validation

        if not validation.valid:
            result.error_message = "Skill validation failed. Use --no-validate to skip."
            return result

    # Load skill to get name
    try:
        skill = Skill.from_directory(skill_dir)
        result.skill_name = skill.name
    except SkillParseError as e:
        result.error_message = f"Failed to parse skill: {e}"
        return result

    # Determine output path
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = skill_dir.parent / f"{skill.name}_{timestamp}.zip"

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Create zip file
    try:
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            file_count = 0
            total_size = 0

            for file_path in _iter_skill_files(skill_dir, include_hidden):
                # Calculate relative path from skill directory
                rel_path = file_path.relative_to(skill_dir)

                # Add to zip
                zf.write(file_path, rel_path)

                file_count += 1
                total_size += file_path.stat().st_size

            result.file_count = file_count
            result.total_size = total_size

    except Exception as e:
        result.error_message = f"Failed to create zip file: {e}"
        return result

    result.success = True
    result.output_path = output_path

    return result


def _iter_skill_files(
    skill_dir: Path, include_hidden: bool = False
) -> Generator[Path, None, None]:
    """Iterate over all files in a skill directory.

    Args:
        skill_dir: Path to the skill directory
        include_hidden: If True, include hidden files

    Yields:
        Path objects for each file

    Note:
        Symlinks are skipped for security (prevent escaping skill_dir).
    """
    resolved_skill_dir = skill_dir.resolve()

    for item in skill_dir.rglob("*"):
        if not item.is_file():
            continue

        # Skip symlinks for security
        if item.is_symlink():
            continue

        # Verify file is within skill directory (prevent traversal)
        try:
            item.resolve().relative_to(resolved_skill_dir)
        except ValueError:
            continue

        # Skip hidden files unless requested
        if not include_hidden:
            # Check if any part of the path is hidden
            parts = item.relative_to(skill_dir).parts
            if any(part.startswith(".") for part in parts):
                continue

        # Skip common unwanted files
        if item.name in ("__pycache__", ".DS_Store", "Thumbs.db"):
            continue

        if item.suffix in (".pyc", ".pyo"):
            continue

        yield item


def extract_skill(
    zip_path: Path,
    output_dir: Path,
    force: bool = False,
) -> Path:
    """Extract a skill from a zip file.

    Args:
        zip_path: Path to the zip file
        output_dir: Directory to extract into
        force: If True, overwrite existing files

    Returns:
        Path to the extracted skill directory

    Raises:
        FileExistsError: If output exists and force is False
        ValueError: If zip is invalid
    """
    if not zip_path.exists():
        raise FileNotFoundError(f"Zip file not found: {zip_path}")

    # Determine skill directory name from zip
    with zipfile.ZipFile(zip_path, "r") as zf:
        # Check if SKILL.md exists
        names = zf.namelist()

        # Find SKILL.md - could be at root or in a subdirectory
        skill_md_paths = [n for n in names if n.endswith("SKILL.md")]
        if not skill_md_paths:
            raise ValueError("Invalid skill zip: SKILL.md not found")

        # Determine the root directory
        skill_md_path = skill_md_paths[0]
        if "/" in skill_md_path:
            root_dir = skill_md_path.rsplit("/", 1)[0]
        else:
            root_dir = ""

    # Extract to output directory
    skill_dir_name = zip_path.stem.split("_")[0]  # Remove timestamp if present
    skill_dir = output_dir / skill_dir_name

    if skill_dir.exists() and not force:
        raise FileExistsError(f"Skill directory already exists: {skill_dir}")

    skill_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zf:
        for name in zf.namelist():
            # Strip root directory if present
            if root_dir and name.startswith(root_dir + "/"):
                rel_name = name[len(root_dir) + 1:]
            else:
                rel_name = name

            if not rel_name:
                continue

            # Security check - prevent path traversal
            # Check for ".." components that could escape the directory
            if ".." in rel_name.split("/"):
                raise ValueError(f"Path traversal detected in zip: {name}")

            dest_path = skill_dir / rel_name
            try:
                dest_path.resolve().relative_to(skill_dir.resolve())
            except ValueError:
                raise ValueError(f"Invalid path in zip: {name}")

            if name.endswith("/"):
                dest_path.mkdir(parents=True, exist_ok=True)
            else:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(name) as src, open(dest_path, "wb") as dst:
                    dst.write(src.read())

    return skill_dir


def list_bundle_contents(zip_path: Path) -> list[dict]:
    """List contents of a skill bundle.

    Args:
        zip_path: Path to the zip file

    Returns:
        List of file info dictionaries
    """
    if not zip_path.exists():
        raise FileNotFoundError(f"Zip file not found: {zip_path}")

    contents = []

    with zipfile.ZipFile(zip_path, "r") as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue

            contents.append({
                "name": info.filename,
                "size": info.file_size,
                "compressed_size": info.compress_size,
                "modified": datetime(*info.date_time).isoformat(),
            })

    return contents
