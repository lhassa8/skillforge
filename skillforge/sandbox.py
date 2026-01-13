"""Sandbox management for SkillForge skill execution."""

import shutil
import subprocess
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from skillforge.config import load_config


class SandboxError(Exception):
    """Raised when sandbox operations fail."""

    pass


def generate_run_id() -> str:
    """Generate a unique run ID.

    Returns:
        Run ID in format: YYYYMMDD_HHMMSS_uuid8
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique = uuid.uuid4().hex[:8]
    return f"{timestamp}_{unique}"


def get_sandbox_path(skill_dir: Path, run_id: str) -> Path:
    """Get the sandbox path for a run.

    Args:
        skill_dir: Path to the skill directory
        run_id: Unique run identifier

    Returns:
        Path to the sandbox directory
    """
    return skill_dir / "reports" / f"run_{run_id}" / "sandbox"


def get_reports_path(skill_dir: Path, run_id: str) -> Path:
    """Get the reports path for a run.

    Args:
        skill_dir: Path to the skill directory
        run_id: Unique run identifier

    Returns:
        Path to the reports directory for this run
    """
    return skill_dir / "reports" / f"run_{run_id}"


def create_sandbox(
    target_dir: Path,
    sandbox_dir: Path,
    ignore_patterns: Optional[list[str]] = None,
) -> Path:
    """Create a sandbox by copying the target directory.

    Args:
        target_dir: Source directory to copy
        sandbox_dir: Destination sandbox directory
        ignore_patterns: Glob patterns to ignore during copy

    Returns:
        Path to the created sandbox directory

    Raises:
        SandboxError: If sandbox creation fails
    """
    if not target_dir.exists():
        raise SandboxError(f"Target directory not found: {target_dir}")

    if not target_dir.is_dir():
        raise SandboxError(f"Target is not a directory: {target_dir}")

    # Create sandbox parent directories
    sandbox_dir.parent.mkdir(parents=True, exist_ok=True)

    # Load config for ignore patterns
    config = load_config()
    all_ignore_patterns = config.get("ignore_paths", [])
    if ignore_patterns:
        all_ignore_patterns.extend(ignore_patterns)

    # Try rsync first (preferred), fall back to shutil
    if _has_rsync():
        _copy_with_rsync(target_dir, sandbox_dir, all_ignore_patterns)
    else:
        _copy_with_shutil(target_dir, sandbox_dir, all_ignore_patterns)

    return sandbox_dir


def _has_rsync() -> bool:
    """Check if rsync is available."""
    return shutil.which("rsync") is not None


def _copy_with_rsync(
    source: Path,
    dest: Path,
    ignore_patterns: list[str],
) -> None:
    """Copy directory using rsync.

    Args:
        source: Source directory
        dest: Destination directory
        ignore_patterns: Patterns to exclude
    """
    cmd = ["rsync", "-a", "--delete"]

    # Add exclude patterns
    for pattern in ignore_patterns:
        cmd.extend(["--exclude", pattern])

    # Ensure trailing slash on source to copy contents
    cmd.append(f"{source}/")
    cmd.append(str(dest))

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )
        if result.returncode != 0:
            raise SandboxError(f"rsync failed: {result.stderr}")
    except subprocess.TimeoutExpired:
        raise SandboxError("rsync timed out after 5 minutes")
    except Exception as e:
        raise SandboxError(f"rsync error: {e}")


def _copy_with_shutil(
    source: Path,
    dest: Path,
    ignore_patterns: list[str],
) -> None:
    """Copy directory using shutil.

    Args:
        source: Source directory
        dest: Destination directory
        ignore_patterns: Patterns to ignore
    """
    import fnmatch

    def ignore_func(directory: str, files: list[str]) -> list[str]:
        """Return files to ignore based on patterns."""
        ignored = []
        for f in files:
            for pattern in ignore_patterns:
                if fnmatch.fnmatch(f, pattern):
                    ignored.append(f)
                    break
        return ignored

    try:
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(source, dest, ignore=ignore_func)
    except Exception as e:
        raise SandboxError(f"Copy failed: {e}")


def load_ignore_patterns(skill_dir: Path, target_dir: Path) -> list[str]:
    """Load ignore patterns from various sources.

    Args:
        skill_dir: Path to the skill directory
        target_dir: Path to the target directory

    Returns:
        Combined list of ignore patterns
    """
    patterns = []

    # Load from config
    config = load_config()
    patterns.extend(config.get("ignore_paths", []))

    # Load from target/.skillforgeignore
    target_ignore = target_dir / ".skillforgeignore"
    if target_ignore.exists():
        patterns.extend(_read_ignore_file(target_ignore))

    # Load from skill/.skillforgeignore
    skill_ignore = skill_dir / ".skillforgeignore"
    if skill_ignore.exists():
        patterns.extend(_read_ignore_file(skill_ignore))

    return patterns


def _read_ignore_file(path: Path) -> list[str]:
    """Read patterns from an ignore file.

    Args:
        path: Path to the ignore file

    Returns:
        List of patterns from the file
    """
    patterns = []
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith("#"):
                    patterns.append(line)
    except Exception:
        pass  # Ignore errors reading ignore files
    return patterns
