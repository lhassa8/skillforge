"""Publish skills to the SkillForge Hub."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from skillforge.hub.client import HUB_REPO


@dataclass
class PublishResult:
    """Result of a publish operation."""

    success: bool
    pr_url: Optional[str] = None
    error: Optional[str] = None


def check_gh_cli() -> bool:
    """Check if the GitHub CLI is installed and authenticated."""
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def get_gh_username() -> Optional[str]:
    """Get the authenticated GitHub username."""
    try:
        result = subprocess.run(
            ["gh", "api", "user", "-q", ".login"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except FileNotFoundError:
        return None


def fork_hub_repo() -> Optional[str]:
    """Fork the hub repo if not already forked. Returns fork URL."""
    try:
        # Check if fork already exists
        username = get_gh_username()
        if not username:
            return None

        # Try to get existing fork
        result = subprocess.run(
            ["gh", "api", f"repos/{username}/skillforge-hub", "-q", ".html_url"],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            return result.stdout.strip()

        # Create fork
        result = subprocess.run(
            ["gh", "repo", "fork", HUB_REPO, "--clone=false"],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            return f"https://github.com/{username}/skillforge-hub"

        return None
    except FileNotFoundError:
        return None


def _get_skill_metadata(skill_path: Path) -> dict:
    """Extract metadata from skill's SKILL.md frontmatter."""
    import yaml

    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        return {}

    content = skill_md.read_text()
    if not content.startswith("---"):
        return {}

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}

    try:
        return yaml.safe_load(parts[1]) or {}
    except Exception:
        return {}


def publish_skill(
    skill_path: Path,
    message: Optional[str] = None,
) -> PublishResult:
    """Publish a skill to the SkillForge Hub.

    This will:
    1. Validate the skill
    2. Fork the hub repo (if needed)
    3. Create a branch with the skill
    4. Open a pull request

    Args:
        skill_path: Path to the skill directory
        message: Optional PR description

    Returns:
        PublishResult with success status and PR URL
    """
    from skillforge.validator import validate_skill_directory

    # Validate skill first
    result = validate_skill_directory(skill_path)
    if not result.valid:
        return PublishResult(
            success=False,
            error=f"Skill validation failed: {', '.join(result.errors)}",
        )

    skill = result.skill
    if not skill:
        return PublishResult(success=False, error="Could not parse skill")

    # Get additional metadata from frontmatter
    metadata = _get_skill_metadata(skill_path)
    author = metadata.get("author", "community")
    version = skill.version or metadata.get("version", "1.0.0")
    tags = metadata.get("tags", [])

    # Check gh CLI
    if not check_gh_cli():
        return PublishResult(
            success=False,
            error="GitHub CLI (gh) not installed or not authenticated. "
            "Install from https://cli.github.com and run 'gh auth login'",
        )

    username = get_gh_username()
    if not username:
        return PublishResult(success=False, error="Could not get GitHub username")

    # Fork the repo
    fork_url = fork_hub_repo()
    if not fork_url:
        return PublishResult(success=False, error="Could not fork hub repository")

    # Clone fork to temp directory and add skill
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Clone the fork
        clone_result = subprocess.run(
            ["gh", "repo", "clone", f"{username}/skillforge-hub", str(tmpdir_path)],
            capture_output=True,
            text=True,
        )

        if clone_result.returncode != 0:
            return PublishResult(
                success=False,
                error=f"Could not clone fork: {clone_result.stderr}",
            )

        # Add upstream remote and fetch
        subprocess.run(
            ["git", "-C", str(tmpdir_path), "remote", "add", "upstream", f"https://github.com/{HUB_REPO}.git"],
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(tmpdir_path), "fetch", "upstream"],
            capture_output=True,
        )

        # Create branch from upstream/main
        branch_name = f"add-skill-{skill.name}"
        subprocess.run(
            ["git", "-C", str(tmpdir_path), "checkout", "-b", branch_name, "upstream/main"],
            capture_output=True,
        )

        # Copy skill to skills directory
        skills_dir = tmpdir_path / "skills" / skill.name
        if skills_dir.exists():
            shutil.rmtree(skills_dir)
        shutil.copytree(skill_path, skills_dir)

        # Stage and commit
        subprocess.run(
            ["git", "-C", str(tmpdir_path), "add", "."],
            capture_output=True,
        )

        commit_msg = f"Add skill: {skill.name}\n\n{skill.description}"
        commit_result = subprocess.run(
            ["git", "-C", str(tmpdir_path), "commit", "-m", commit_msg],
            capture_output=True,
            text=True,
        )

        if commit_result.returncode != 0:
            # Check if nothing to commit (skill already exists identically)
            if "nothing to commit" in commit_result.stdout:
                return PublishResult(
                    success=False,
                    error="No changes to publish - skill already exists with same content",
                )
            return PublishResult(
                success=False,
                error=f"Could not commit: {commit_result.stderr}",
            )

        # Push to fork
        push_result = subprocess.run(
            ["git", "-C", str(tmpdir_path), "push", "-u", "origin", branch_name, "--force"],
            capture_output=True,
            text=True,
        )

        if push_result.returncode != 0:
            return PublishResult(
                success=False,
                error=f"Could not push to fork: {push_result.stderr}",
            )

        # Create pull request
        pr_title = f"Add skill: {skill.name}"
        pr_body = f"""## New Skill Submission

**Name:** {skill.name}
**Version:** {version}
**Author:** {author}

### Description
{skill.description}

### Tags
{', '.join(tags) if tags else 'None'}

---
{message or ''}

Submitted via `skillforge hub publish`
"""

        pr_result = subprocess.run(
            [
                "gh", "pr", "create",
                "--repo", HUB_REPO,
                "--head", f"{username}:{branch_name}",
                "--title", pr_title,
                "--body", pr_body,
            ],
            capture_output=True,
            text=True,
            cwd=str(tmpdir_path),
        )

        if pr_result.returncode != 0:
            # Check if PR already exists
            if "already exists" in pr_result.stderr:
                # Get existing PR URL
                list_result = subprocess.run(
                    [
                        "gh", "pr", "list",
                        "--repo", HUB_REPO,
                        "--head", f"{username}:{branch_name}",
                        "--json", "url",
                        "-q", ".[0].url",
                    ],
                    capture_output=True,
                    text=True,
                )
                if list_result.returncode == 0 and list_result.stdout.strip():
                    return PublishResult(
                        success=True,
                        pr_url=list_result.stdout.strip(),
                    )

            return PublishResult(
                success=False,
                error=f"Could not create pull request: {pr_result.stderr}",
            )

        # Extract PR URL from output
        pr_url = pr_result.stdout.strip()

        return PublishResult(success=True, pr_url=pr_url)
