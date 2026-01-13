"""Testing framework for SkillForge skills."""

import filecmp
import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import yaml

from skillforge.loader import list_fixtures
from skillforge.runner import run_skill, RunReport, get_run_summary
from skillforge.sandbox import create_sandbox, generate_run_id


@dataclass
class FixtureConfig:
    """Configuration for a test fixture."""

    name: str
    inputs: dict[str, Any] = field(default_factory=dict)
    allow_extra_files: bool = False


@dataclass
class ComparisonResult:
    """Result of comparing actual vs expected output."""

    matches: bool = True
    missing_files: list[str] = field(default_factory=list)
    extra_files: list[str] = field(default_factory=list)
    different_files: list[str] = field(default_factory=list)
    message: str = ""


@dataclass
class FixtureResult:
    """Result of running a single fixture test."""

    fixture_name: str
    run_report: Optional[RunReport] = None
    comparison: Optional[ComparisonResult] = None
    golden_comparison: Optional[ComparisonResult] = None
    passed: bool = False
    error_message: str = ""
    duration_ms: int = 0


@dataclass
class SkillTestReport:
    """Complete test report for a skill."""

    skill_name: str
    skill_dir: str
    started_at: str
    finished_at: str = ""
    fixtures: list[FixtureResult] = field(default_factory=list)
    total_passed: int = 0
    total_failed: int = 0
    total_skipped: int = 0

    @property
    def all_passed(self) -> bool:
        """Check if all fixtures passed."""
        return self.total_failed == 0 and self.total_passed > 0


def load_fixture_config(fixture_dir: Path) -> FixtureConfig:
    """Load fixture configuration from fixture.yaml.

    Args:
        fixture_dir: Path to the fixture directory

    Returns:
        FixtureConfig with settings from fixture.yaml or defaults
    """
    config_file = fixture_dir / "fixture.yaml"
    config = FixtureConfig(name=fixture_dir.name)

    if config_file.exists():
        try:
            with open(config_file) as f:
                data = yaml.safe_load(f) or {}

            config.inputs = data.get("inputs", {})
            config.allow_extra_files = data.get("allow_extra_files", False)
        except Exception:
            pass  # Use defaults on error

    return config


def discover_fixtures(skill_dir: Path) -> list[Path]:
    """Discover all fixture directories in a skill.

    Args:
        skill_dir: Path to the skill directory

    Returns:
        List of fixture directory paths
    """
    fixtures_dir = skill_dir / "fixtures"
    if not fixtures_dir.is_dir():
        return []

    fixtures = []
    for item in sorted(fixtures_dir.iterdir()):
        if item.is_dir() and not item.name.startswith("."):
            # Must have at least an input directory
            if (item / "input").is_dir():
                fixtures.append(item)

    return fixtures


def run_fixture_test(
    skill_dir: Path,
    fixture_dir: Path,
    run_id: str,
) -> FixtureResult:
    """Run a single fixture test.

    Args:
        skill_dir: Path to the skill directory
        fixture_dir: Path to the fixture directory
        run_id: Unique run identifier

    Returns:
        FixtureResult with test outcome
    """
    fixture_name = fixture_dir.name
    start_time = datetime.now()

    result = FixtureResult(fixture_name=fixture_name)

    try:
        # Load fixture config
        config = load_fixture_config(fixture_dir)

        # Get paths
        input_dir = fixture_dir / "input"
        expected_dir = fixture_dir / "expected"
        golden_dir = fixture_dir / "_golden"

        if not input_dir.is_dir():
            result.error_message = f"Fixture input directory not found: {input_dir}"
            return result

        # Create sandbox directory path
        sandbox_dir = skill_dir / "reports" / f"test_{run_id}" / fixture_name / "sandbox"

        # Run the skill (run_skill will create the sandbox from input_dir)
        report = run_skill(
            skill_dir=skill_dir,
            target_dir=input_dir,  # Source for sandbox
            sandbox_dir=sandbox_dir,
            no_sandbox=False,
            input_overrides=config.inputs,
        )

        result.run_report = report

        # Check if skill execution succeeded
        if not report.success:
            result.error_message = f"Skill execution failed: {report.error_message}"
            result.passed = False
            return result

        # Compare against expected/ if it exists
        if expected_dir.is_dir():
            result.comparison = compare_directories(
                sandbox_dir,
                expected_dir,
                allow_extra=config.allow_extra_files,
            )
            if not result.comparison.matches:
                result.error_message = f"Output does not match expected: {result.comparison.message}"
                result.passed = False
                return result

        # Compare against golden artifacts if they exist
        if golden_dir.is_dir():
            result.golden_comparison = compare_golden(sandbox_dir, golden_dir)
            if not result.golden_comparison.matches:
                result.error_message = f"Golden comparison failed: {result.golden_comparison.message}"
                result.passed = False
                return result

        # All checks passed
        result.passed = True

    except Exception as e:
        result.error_message = str(e)
        result.passed = False

    result.duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
    return result


def compare_directories(
    actual_dir: Path,
    expected_dir: Path,
    allow_extra: bool = False,
) -> ComparisonResult:
    """Compare actual output directory against expected.

    Args:
        actual_dir: Directory with actual output
        expected_dir: Directory with expected output
        allow_extra: If True, allow extra files in actual

    Returns:
        ComparisonResult with comparison details
    """
    result = ComparisonResult()

    # Get all files in expected (relative paths)
    expected_files = set()
    for root, _, files in os.walk(expected_dir):
        for f in files:
            if f.startswith("."):
                continue
            rel_path = os.path.relpath(os.path.join(root, f), expected_dir)
            expected_files.add(rel_path)

    # Get all files in actual (relative paths)
    actual_files = set()
    for root, _, files in os.walk(actual_dir):
        for f in files:
            if f.startswith("."):
                continue
            rel_path = os.path.relpath(os.path.join(root, f), actual_dir)
            actual_files.add(rel_path)

    # Find missing files (in expected but not in actual)
    result.missing_files = sorted(expected_files - actual_files)

    # Find extra files (in actual but not in expected)
    if not allow_extra:
        result.extra_files = sorted(actual_files - expected_files)

    # Compare common files
    common_files = expected_files & actual_files
    for rel_path in sorted(common_files):
        actual_file = actual_dir / rel_path
        expected_file = expected_dir / rel_path

        if not _files_match(actual_file, expected_file):
            result.different_files.append(rel_path)

    # Determine overall match
    if result.missing_files or result.extra_files or result.different_files:
        result.matches = False
        parts = []
        if result.missing_files:
            parts.append(f"{len(result.missing_files)} missing")
        if result.extra_files:
            parts.append(f"{len(result.extra_files)} extra")
        if result.different_files:
            parts.append(f"{len(result.different_files)} different")
        result.message = ", ".join(parts)
    else:
        result.matches = True
        result.message = "All files match"

    return result


def compare_golden(actual_dir: Path, golden_dir: Path) -> ComparisonResult:
    """Compare actual output against golden artifacts.

    Args:
        actual_dir: Directory with actual output
        golden_dir: Directory with golden artifacts

    Returns:
        ComparisonResult with comparison details
    """
    result = ComparisonResult()

    # Load expected changed files
    changed_files_path = golden_dir / "expected_changed_files.json"
    hashes_path = golden_dir / "expected_hashes.json"

    if not changed_files_path.exists():
        result.matches = True
        result.message = "No golden artifacts to compare"
        return result

    try:
        with open(changed_files_path) as f:
            expected_changed = set(json.load(f))
    except Exception as e:
        result.matches = False
        result.message = f"Failed to load golden changed files: {e}"
        return result

    # Get actual changed files (all files in actual_dir)
    actual_files = set()
    for root, _, files in os.walk(actual_dir):
        for f in files:
            if f.startswith("."):
                continue
            rel_path = os.path.relpath(os.path.join(root, f), actual_dir)
            actual_files.add(rel_path)

    # Compare file sets
    result.missing_files = sorted(expected_changed - actual_files)
    result.extra_files = sorted(actual_files - expected_changed)

    # Compare hashes if available
    if hashes_path.exists():
        try:
            with open(hashes_path) as f:
                expected_hashes = json.load(f)

            for rel_path, expected_hash in expected_hashes.items():
                actual_file = actual_dir / rel_path
                if actual_file.exists():
                    actual_hash = _hash_file(actual_file)
                    if actual_hash != expected_hash:
                        result.different_files.append(rel_path)
        except Exception:
            pass  # Skip hash comparison on error

    # Determine overall match
    if result.missing_files or result.extra_files or result.different_files:
        result.matches = False
        parts = []
        if result.missing_files:
            parts.append(f"{len(result.missing_files)} missing")
        if result.extra_files:
            parts.append(f"{len(result.extra_files)} extra")
        if result.different_files:
            parts.append(f"{len(result.different_files)} different")
        result.message = ", ".join(parts)
    else:
        result.matches = True
        result.message = "Golden comparison passed"

    return result


def run_all_fixtures(skill_dir: Path) -> SkillTestReport:
    """Run all fixture tests for a skill.

    Args:
        skill_dir: Path to the skill directory

    Returns:
        SkillTestReport with all fixture results
    """
    from skillforge.loader import load_skill_yaml

    started_at = datetime.now().isoformat()
    run_id = generate_run_id()

    # Load skill name
    try:
        skill_data = load_skill_yaml(skill_dir)
        skill_name = skill_data.get("name", "unknown")
    except Exception:
        skill_name = skill_dir.name

    report = SkillTestReport(
        skill_name=skill_name,
        skill_dir=str(skill_dir),
        started_at=started_at,
    )

    # Discover fixtures
    fixtures = discover_fixtures(skill_dir)

    if not fixtures:
        report.total_skipped = 1
        report.finished_at = datetime.now().isoformat()
        return report

    # Run each fixture
    for fixture_dir in fixtures:
        fixture_result = run_fixture_test(skill_dir, fixture_dir, run_id)
        report.fixtures.append(fixture_result)

        if fixture_result.passed:
            report.total_passed += 1
        else:
            report.total_failed += 1

    report.finished_at = datetime.now().isoformat()

    # Write test report
    _write_test_report(skill_dir, run_id, report)

    return report


def _files_match(file1: Path, file2: Path) -> bool:
    """Check if two files have identical content.

    Args:
        file1: First file path
        file2: Second file path

    Returns:
        True if files match, False otherwise
    """
    # Try text comparison first
    try:
        return file1.read_text() == file2.read_text()
    except UnicodeDecodeError:
        # Binary comparison
        return file1.read_bytes() == file2.read_bytes()


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


def _write_test_report(skill_dir: Path, run_id: str, report: SkillTestReport) -> None:
    """Write test report to disk.

    Args:
        skill_dir: Path to the skill directory
        run_id: Run identifier
        report: Test report to write
    """
    reports_dir = skill_dir / "reports" / f"test_{run_id}"
    reports_dir.mkdir(parents=True, exist_ok=True)

    # Convert to dict for JSON serialization
    report_dict = {
        "skill_name": report.skill_name,
        "skill_dir": report.skill_dir,
        "started_at": report.started_at,
        "finished_at": report.finished_at,
        "total_passed": report.total_passed,
        "total_failed": report.total_failed,
        "total_skipped": report.total_skipped,
        "fixtures": [],
    }

    for fixture in report.fixtures:
        fixture_dict = {
            "fixture_name": fixture.fixture_name,
            "passed": fixture.passed,
            "error_message": fixture.error_message,
            "duration_ms": fixture.duration_ms,
        }
        if fixture.run_report:
            fixture_dict["run_summary"] = get_run_summary(fixture.run_report)
        if fixture.comparison:
            fixture_dict["comparison"] = {
                "matches": fixture.comparison.matches,
                "missing_files": fixture.comparison.missing_files,
                "extra_files": fixture.comparison.extra_files,
                "different_files": fixture.comparison.different_files,
                "message": fixture.comparison.message,
            }
        report_dict["fixtures"].append(fixture_dict)

    report_file = reports_dir / "test_report.json"
    with open(report_file, "w") as f:
        json.dump(report_dict, f, indent=2)
