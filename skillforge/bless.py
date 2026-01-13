"""Bless command for creating golden regression artifacts."""

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from skillforge.runner import run_skill, RunReport
from skillforge.sandbox import generate_run_id


@dataclass
class BlessResult:
    """Result of blessing a fixture."""

    fixture_name: str
    success: bool = False
    error_message: str = ""
    run_report: Optional[RunReport] = None
    changed_files: list[str] = None
    golden_dir: str = ""

    def __post_init__(self):
        if self.changed_files is None:
            self.changed_files = []


def bless_fixture(
    skill_dir: Path,
    fixture_name: str,
) -> BlessResult:
    """Run a skill on a fixture and store golden artifacts.

    Args:
        skill_dir: Path to the skill directory
        fixture_name: Name of the fixture to bless

    Returns:
        BlessResult with outcome details
    """
    result = BlessResult(fixture_name=fixture_name)

    # Validate paths
    fixture_dir = skill_dir / "fixtures" / fixture_name
    if not fixture_dir.is_dir():
        result.error_message = f"Fixture not found: {fixture_name}"
        return result

    input_dir = fixture_dir / "input"
    if not input_dir.is_dir():
        result.error_message = f"Fixture input directory not found: {input_dir}"
        return result

    # Create sandbox for the run
    run_id = generate_run_id()
    sandbox_dir = skill_dir / "reports" / f"bless_{run_id}" / fixture_name / "sandbox"

    try:
        # Run the skill
        report = run_skill(
            skill_dir=skill_dir,
            target_dir=input_dir,
            sandbox_dir=sandbox_dir,
            no_sandbox=False,
        )
        result.run_report = report

        if not report.success:
            result.error_message = f"Skill execution failed: {report.error_message}"
            return result

        # Collect changed files and their hashes
        changed_files = []
        file_hashes = {}

        for root, _, files in os.walk(sandbox_dir):
            for f in files:
                if f.startswith("."):
                    continue
                file_path = Path(root) / f
                rel_path = os.path.relpath(file_path, sandbox_dir)
                changed_files.append(rel_path)
                file_hashes[rel_path] = _hash_file(file_path)

        result.changed_files = sorted(changed_files)

        # Create golden directory
        golden_dir = fixture_dir / "_golden"
        golden_dir.mkdir(parents=True, exist_ok=True)
        result.golden_dir = str(golden_dir)

        # Write golden artifacts
        _write_golden_artifacts(golden_dir, result.changed_files, file_hashes, report)

        result.success = True

    except Exception as e:
        result.error_message = str(e)

    return result


def _hash_file(file_path: Path) -> str:
    """Compute SHA256 hash of a file.

    Args:
        file_path: Path to the file

    Returns:
        Hex digest of the hash
    """
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _write_golden_artifacts(
    golden_dir: Path,
    changed_files: list[str],
    file_hashes: dict[str, str],
    report: RunReport,
) -> None:
    """Write golden artifacts to disk.

    Args:
        golden_dir: Directory to write artifacts to
        changed_files: List of changed file paths
        file_hashes: Map of file paths to their hashes
        report: Run report for metadata
    """
    # Write expected changed files
    changed_files_path = golden_dir / "expected_changed_files.json"
    with open(changed_files_path, "w") as f:
        json.dump(changed_files, f, indent=2)

    # Write expected hashes
    hashes_path = golden_dir / "expected_hashes.json"
    with open(hashes_path, "w") as f:
        json.dump(file_hashes, f, indent=2, sort_keys=True)

    # Write metadata
    metadata = {
        "blessed_at": datetime.now().isoformat(),
        "run_id": report.run_id,
        "skill_name": report.skill_name,
        "steps_count": len(report.steps),
        "checks_count": len(report.checks),
    }
    metadata_path = golden_dir / "bless_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)


def get_golden_info(skill_dir: Path, fixture_name: str) -> dict:
    """Get information about existing golden artifacts.

    Args:
        skill_dir: Path to the skill directory
        fixture_name: Name of the fixture

    Returns:
        Dictionary with golden artifact info, or empty dict if none exist
    """
    golden_dir = skill_dir / "fixtures" / fixture_name / "_golden"

    if not golden_dir.is_dir():
        return {}

    info = {"exists": True, "path": str(golden_dir)}

    # Load metadata if available
    metadata_path = golden_dir / "bless_metadata.json"
    if metadata_path.exists():
        try:
            with open(metadata_path) as f:
                info["metadata"] = json.load(f)
        except Exception:
            pass

    # Count files
    changed_files_path = golden_dir / "expected_changed_files.json"
    if changed_files_path.exists():
        try:
            with open(changed_files_path) as f:
                files = json.load(f)
                info["file_count"] = len(files)
        except Exception:
            pass

    return info
