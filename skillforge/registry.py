"""Skill registry for discovering and downloading skills from GitHub."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


# Config stored at ~/.config/skillforge/registries.json
REGISTRIES_CONFIG = Path.home() / ".config" / "skillforge" / "registries.json"


@dataclass
class SkillEntry:
    """A skill listed in a registry."""

    name: str
    description: str
    version: str
    repo: str
    author: str = ""
    tags: list[str] = field(default_factory=list)
    updated: str = ""
    registry: str = ""  # Which registry this came from


@dataclass
class Registry:
    """A skill registry."""

    name: str
    url: str
    description: str = ""
    skills: list[SkillEntry] = field(default_factory=list)
    added: str = ""
    fetched: str = ""


class RegistryError(Exception):
    """Base exception for registry operations."""

    pass


class RegistryNotFoundError(RegistryError):
    """Registry not found."""

    pass


class SkillNotFoundError(RegistryError):
    """Skill not found in any registry."""

    pass


def _load_config() -> dict:
    """Load the registries config file."""
    if not REGISTRIES_CONFIG.exists():
        return {"registries": [], "cache": {}}

    try:
        return json.loads(REGISTRIES_CONFIG.read_text())
    except (json.JSONDecodeError, OSError):
        return {"registries": [], "cache": {}}


def _save_config(config: dict) -> None:
    """Save the registries config file."""
    REGISTRIES_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    REGISTRIES_CONFIG.write_text(json.dumps(config, indent=2))


def _github_url_to_raw(url: str, file_path: str = "index.json") -> str:
    """Convert a GitHub repo URL to raw content URL.

    Examples:
        https://github.com/user/repo -> https://raw.githubusercontent.com/user/repo/main/index.json
        https://github.com/user/repo/tree/branch -> https://raw.githubusercontent.com/user/repo/branch/index.json
    """
    # Remove trailing slash
    url = url.rstrip("/")

    # Handle github.com URLs
    match = re.match(r"https?://github\.com/([^/]+)/([^/]+)(?:/tree/([^/]+))?", url)
    if match:
        owner, repo, branch = match.groups()
        branch = branch or "main"
        return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{file_path}"

    # Already a raw URL or other format
    if "raw.githubusercontent.com" in url:
        if not url.endswith(file_path):
            return f"{url}/{file_path}"
        return url

    raise RegistryError(f"Invalid GitHub URL: {url}")


def _extract_registry_name(url: str) -> str:
    """Extract a registry name from its URL."""
    match = re.match(r"https?://github\.com/[^/]+/([^/]+)", url)
    if match:
        return match.group(1)

    # Fallback to last path component
    return url.rstrip("/").split("/")[-1]


def _fetch_index(url: str) -> dict:
    """Fetch and parse index.json from a registry URL."""
    raw_url = _github_url_to_raw(url)

    try:
        req = urllib.request.Request(
            raw_url,
            headers={"User-Agent": "SkillForge/0.7.0"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise RegistryError(f"Registry index not found at {raw_url}")
        raise RegistryError(f"Failed to fetch registry: {e}")
    except urllib.error.URLError as e:
        raise RegistryError(f"Network error fetching registry: {e}")
    except json.JSONDecodeError as e:
        raise RegistryError(f"Invalid JSON in registry index: {e}")


def add_registry(url: str, name: Optional[str] = None) -> Registry:
    """Add a registry by GitHub URL.

    Fetches index.json and saves to config.

    Args:
        url: GitHub repository URL
        name: Optional custom name for the registry

    Returns:
        The added Registry

    Raises:
        RegistryError: If the registry cannot be fetched or is invalid
    """
    config = _load_config()

    # Extract or use provided name
    registry_name = name or _extract_registry_name(url)

    # Check if already exists
    for reg in config["registries"]:
        if reg["name"] == registry_name:
            raise RegistryError(f"Registry '{registry_name}' already exists")

    # Fetch the index
    index_data = _fetch_index(url)

    # Validate index structure
    if "skills" not in index_data:
        raise RegistryError("Invalid registry: missing 'skills' field in index.json")

    # Parse skills
    skills = []
    for skill_data in index_data.get("skills", []):
        skills.append(
            SkillEntry(
                name=skill_data.get("name", ""),
                description=skill_data.get("description", ""),
                version=skill_data.get("version", "0.0.0"),
                repo=skill_data.get("repo", ""),
                author=skill_data.get("author", ""),
                tags=skill_data.get("tags", []),
                updated=skill_data.get("updated", ""),
                registry=registry_name,
            )
        )

    # Create registry entry
    now = datetime.now().isoformat()
    registry = Registry(
        name=registry_name,
        url=url,
        description=index_data.get("description", ""),
        skills=skills,
        added=now,
        fetched=now,
    )

    # Save to config
    config["registries"].append(
        {
            "name": registry_name,
            "url": url,
            "added": now,
        }
    )
    config["cache"][registry_name] = {
        "fetched": now,
        "description": registry.description,
        "skills": [
            {
                "name": s.name,
                "description": s.description,
                "version": s.version,
                "repo": s.repo,
                "author": s.author,
                "tags": s.tags,
                "updated": s.updated,
            }
            for s in skills
        ],
    }
    _save_config(config)

    return registry


def remove_registry(name: str) -> bool:
    """Remove a registry by name.

    Args:
        name: Registry name to remove

    Returns:
        True if removed, False if not found
    """
    config = _load_config()

    # Find and remove
    original_count = len(config["registries"])
    config["registries"] = [r for r in config["registries"] if r["name"] != name]

    if len(config["registries"]) == original_count:
        return False

    # Remove from cache
    config["cache"].pop(name, None)
    _save_config(config)

    return True


def list_registries() -> list[Registry]:
    """List all configured registries.

    Returns:
        List of Registry objects with cached skill data
    """
    config = _load_config()
    registries = []

    for reg_data in config["registries"]:
        name = reg_data["name"]
        cache = config["cache"].get(name, {})

        skills = []
        for skill_data in cache.get("skills", []):
            skills.append(
                SkillEntry(
                    name=skill_data.get("name", ""),
                    description=skill_data.get("description", ""),
                    version=skill_data.get("version", "0.0.0"),
                    repo=skill_data.get("repo", ""),
                    author=skill_data.get("author", ""),
                    tags=skill_data.get("tags", []),
                    updated=skill_data.get("updated", ""),
                    registry=name,
                )
            )

        registries.append(
            Registry(
                name=name,
                url=reg_data["url"],
                description=cache.get("description", ""),
                skills=skills,
                added=reg_data.get("added", ""),
                fetched=cache.get("fetched", ""),
            )
        )

    return registries


def update_registries() -> list[Registry]:
    """Refresh all registry indexes from GitHub.

    Returns:
        List of updated Registry objects
    """
    config = _load_config()
    updated_registries = []

    for reg_data in config["registries"]:
        name = reg_data["name"]
        url = reg_data["url"]

        try:
            index_data = _fetch_index(url)
            now = datetime.now().isoformat()

            skills = []
            for skill_data in index_data.get("skills", []):
                skills.append(
                    SkillEntry(
                        name=skill_data.get("name", ""),
                        description=skill_data.get("description", ""),
                        version=skill_data.get("version", "0.0.0"),
                        repo=skill_data.get("repo", ""),
                        author=skill_data.get("author", ""),
                        tags=skill_data.get("tags", []),
                        updated=skill_data.get("updated", ""),
                        registry=name,
                    )
                )

            config["cache"][name] = {
                "fetched": now,
                "description": index_data.get("description", ""),
                "skills": [
                    {
                        "name": s.name,
                        "description": s.description,
                        "version": s.version,
                        "repo": s.repo,
                        "author": s.author,
                        "tags": s.tags,
                        "updated": s.updated,
                    }
                    for s in skills
                ],
            }

            updated_registries.append(
                Registry(
                    name=name,
                    url=url,
                    description=index_data.get("description", ""),
                    skills=skills,
                    added=reg_data.get("added", ""),
                    fetched=now,
                )
            )
        except RegistryError:
            # Keep old cache on error
            cache = config["cache"].get(name, {})
            skills = [
                SkillEntry(
                    name=s.get("name", ""),
                    description=s.get("description", ""),
                    version=s.get("version", "0.0.0"),
                    repo=s.get("repo", ""),
                    registry=name,
                )
                for s in cache.get("skills", [])
            ]
            updated_registries.append(
                Registry(
                    name=name,
                    url=url,
                    description=cache.get("description", ""),
                    skills=skills,
                    added=reg_data.get("added", ""),
                    fetched=cache.get("fetched", ""),
                )
            )

    _save_config(config)
    return updated_registries


def search_skills(query: str, registry: Optional[str] = None) -> list[SkillEntry]:
    """Search for skills across registries.

    Args:
        query: Search query (matches name, description, and tags)
        registry: Optional registry name to limit search

    Returns:
        List of matching SkillEntry objects
    """
    registries = list_registries()
    results = []

    query_lower = query.lower()
    query_terms = query_lower.split()

    for reg in registries:
        if registry and reg.name != registry:
            continue

        for skill in reg.skills:
            # Check if any query term matches
            searchable = f"{skill.name} {skill.description} {' '.join(skill.tags)}".lower()

            if all(term in searchable for term in query_terms):
                results.append(skill)

    # Sort by relevance (name matches first)
    results.sort(key=lambda s: (query_lower not in s.name.lower(), s.name))

    return results


def get_skill_info(
    skill_name: str, registry: Optional[str] = None
) -> Optional[SkillEntry]:
    """Get info about a specific skill.

    Args:
        skill_name: Skill name to look up
        registry: Optional registry to search in

    Returns:
        SkillEntry if found, None otherwise
    """
    registries = list_registries()

    for reg in registries:
        if registry and reg.name != registry:
            continue

        for skill in reg.skills:
            if skill.name == skill_name:
                return skill

    return None


def pull_skill(
    skill_name: str,
    output_dir: Path = Path("./skills"),
    registry: Optional[str] = None,
) -> Path:
    """Download a skill from a registry.

    Args:
        skill_name: Name of the skill to download
        output_dir: Directory to download to
        registry: Optional specific registry to pull from

    Returns:
        Path to the downloaded skill directory

    Raises:
        SkillNotFoundError: If skill not found
        RegistryError: If download fails
    """
    skill = get_skill_info(skill_name, registry)
    if not skill:
        raise SkillNotFoundError(f"Skill '{skill_name}' not found in any registry")

    if not skill.repo:
        raise RegistryError(f"Skill '{skill_name}' has no repository URL")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    skill_dir = output_dir / skill_name

    # Check if already exists
    if skill_dir.exists():
        raise RegistryError(
            f"Skill directory already exists: {skill_dir}. "
            "Remove it first or choose a different output directory."
        )

    # Clone the repo
    repo_url = skill.repo

    # Try git clone first
    if shutil.which("git"):
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                subprocess.run(
                    ["git", "clone", "--depth", "1", repo_url, tmpdir],
                    check=True,
                    capture_output=True,
                    text=True,
                )

                # Find SKILL.md - could be at root or in a subdirectory
                tmp_path = Path(tmpdir)
                skill_md = tmp_path / "SKILL.md"

                if skill_md.exists():
                    # Copy the whole directory
                    shutil.copytree(
                        tmpdir,
                        skill_dir,
                        ignore=shutil.ignore_patterns(".git", ".git*"),
                    )
                else:
                    # Look for skill in subdirectory matching name
                    subdir = tmp_path / skill_name
                    if subdir.exists() and (subdir / "SKILL.md").exists():
                        shutil.copytree(
                            subdir,
                            skill_dir,
                            ignore=shutil.ignore_patterns(".git", ".git*"),
                        )
                    else:
                        raise RegistryError(
                            f"Could not find SKILL.md in cloned repository"
                        )

            return skill_dir

        except subprocess.CalledProcessError as e:
            raise RegistryError(f"Git clone failed: {e.stderr}")

    # Fallback: try downloading as zip
    else:
        # Convert GitHub repo to zip URL
        match = re.match(r"https?://github\.com/([^/]+)/([^/]+)", repo_url)
        if match:
            owner, repo = match.groups()
            zip_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/main.zip"

            try:
                with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
                    req = urllib.request.Request(
                        zip_url,
                        headers={"User-Agent": "SkillForge/0.7.0"},
                    )
                    with urllib.request.urlopen(req, timeout=60) as resp:
                        f.write(resp.read())
                    zip_path = f.name

                # Extract
                import zipfile

                with tempfile.TemporaryDirectory() as tmpdir:
                    with zipfile.ZipFile(zip_path) as zf:
                        zf.extractall(tmpdir)

                    # Find the extracted directory
                    extracted = list(Path(tmpdir).iterdir())
                    if len(extracted) == 1 and extracted[0].is_dir():
                        src = extracted[0]
                        if (src / "SKILL.md").exists():
                            shutil.copytree(src, skill_dir)
                        elif (src / skill_name / "SKILL.md").exists():
                            shutil.copytree(src / skill_name, skill_dir)
                        else:
                            raise RegistryError("Could not find SKILL.md in archive")
                    else:
                        raise RegistryError("Unexpected archive structure")

                os.unlink(zip_path)
                return skill_dir

            except urllib.error.URLError as e:
                raise RegistryError(f"Download failed: {e}")
        else:
            raise RegistryError(
                "Git not available and repo URL is not a GitHub URL. "
                "Please install git to download this skill."
            )
