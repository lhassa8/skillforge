"""Environment verification for SkillForge."""

import shutil
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class CheckStatus(Enum):
    """Status of an environment check."""

    OK = "ok"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class CheckResult:
    """Result of an environment check."""

    name: str
    status: CheckStatus
    message: str
    version: Optional[str] = None


def check_python_version() -> CheckResult:
    """Check if Python version meets requirements (3.11+)."""
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"

    if version.major < 3 or (version.major == 3 and version.minor < 11):
        return CheckResult(
            name="Python",
            status=CheckStatus.ERROR,
            message=f"Python 3.11+ required, found {version_str}",
            version=version_str,
        )

    return CheckResult(
        name="Python",
        status=CheckStatus.OK,
        message=f"Python {version_str}",
        version=version_str,
    )


def check_git() -> CheckResult:
    """Check if git is available."""
    git_path = shutil.which("git")

    if not git_path:
        return CheckResult(
            name="Git",
            status=CheckStatus.ERROR,
            message="git not found in PATH",
        )

    try:
        result = subprocess.run(
            ["git", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            version = result.stdout.strip().replace("git version ", "")
            return CheckResult(
                name="Git",
                status=CheckStatus.OK,
                message=f"git {version}",
                version=version,
            )
        else:
            return CheckResult(
                name="Git",
                status=CheckStatus.ERROR,
                message="git found but failed to run",
            )
    except subprocess.TimeoutExpired:
        return CheckResult(
            name="Git",
            status=CheckStatus.ERROR,
            message="git command timed out",
        )
    except Exception as e:
        return CheckResult(
            name="Git",
            status=CheckStatus.ERROR,
            message=f"git check failed: {e}",
        )


def check_rsync() -> CheckResult:
    """Check if rsync is available (preferred for sandbox copying)."""
    rsync_path = shutil.which("rsync")

    if not rsync_path:
        return CheckResult(
            name="rsync",
            status=CheckStatus.WARNING,
            message="rsync not found (will use shutil.copytree instead)",
        )

    try:
        result = subprocess.run(
            ["rsync", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            # Extract version from first line
            first_line = result.stdout.split("\n")[0]
            version = first_line.split()[2] if len(first_line.split()) > 2 else "unknown"
            return CheckResult(
                name="rsync",
                status=CheckStatus.OK,
                message=f"rsync {version}",
                version=version,
            )
        else:
            return CheckResult(
                name="rsync",
                status=CheckStatus.WARNING,
                message="rsync found but failed to run",
            )
    except subprocess.TimeoutExpired:
        return CheckResult(
            name="rsync",
            status=CheckStatus.WARNING,
            message="rsync command timed out",
        )
    except Exception as e:
        return CheckResult(
            name="rsync",
            status=CheckStatus.WARNING,
            message=f"rsync check failed: {e}",
        )


def check_config_initialized() -> CheckResult:
    """Check if SkillForge config directory is initialized."""
    from skillforge.config import CONFIG_DIR, CONFIG_FILE

    if not CONFIG_DIR.exists():
        return CheckResult(
            name="Config",
            status=CheckStatus.WARNING,
            message=f"Config directory not found. Run 'skillforge init' to create it.",
        )

    if not CONFIG_FILE.exists():
        return CheckResult(
            name="Config",
            status=CheckStatus.WARNING,
            message=f"Config file not found at {CONFIG_FILE}",
        )

    return CheckResult(
        name="Config",
        status=CheckStatus.OK,
        message=f"Config found at {CONFIG_DIR}",
    )


def run_all_checks() -> list[CheckResult]:
    """Run all environment checks and return results."""
    return [
        check_python_version(),
        check_git(),
        check_rsync(),
        check_config_initialized(),
    ]


def has_errors(results: list[CheckResult]) -> bool:
    """Check if any results have error status."""
    return any(r.status == CheckStatus.ERROR for r in results)


def has_warnings(results: list[CheckResult]) -> bool:
    """Check if any results have warning status."""
    return any(r.status == CheckStatus.WARNING for r in results)
