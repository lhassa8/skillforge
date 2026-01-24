"""Hub client for interacting with the SkillForge skill registry."""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Hub configuration
HUB_REPO = "lhassa8/skillforge-hub"
HUB_INDEX_URL = f"https://raw.githubusercontent.com/{HUB_REPO}/main/index.json"
HUB_RAW_URL = f"https://raw.githubusercontent.com/{HUB_REPO}/main/skills"


@dataclass
class HubSkill:
    """Skill metadata from the hub."""

    name: str
    description: str
    author: str
    version: str
    tags: list[str]
    downloads: int = 0
    stars: int = 0

    @classmethod
    def from_dict(cls, data: dict) -> "HubSkill":
        """Create from dictionary."""
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            author=data.get("author", ""),
            version=data.get("version", "1.0.0"),
            tags=data.get("tags", []),
            downloads=data.get("downloads", 0),
            stars=data.get("stars", 0),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "author": self.author,
            "version": self.version,
            "tags": self.tags,
            "downloads": self.downloads,
            "stars": self.stars,
        }


class HubClient:
    """Client for interacting with the SkillForge Hub."""

    def __init__(self, index_url: str = HUB_INDEX_URL, raw_url: str = HUB_RAW_URL):
        self.index_url = index_url
        self.raw_url = raw_url
        self._index: Optional[dict] = None

    def _fetch_index(self) -> dict:
        """Fetch the skill index from the hub."""
        if self._index is not None:
            return self._index

        try:
            with urllib.request.urlopen(self.index_url, timeout=10) as response:
                self._index = json.loads(response.read().decode("utf-8"))
                return self._index
        except urllib.error.URLError as e:
            raise ConnectionError(f"Failed to connect to hub: {e}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid hub index: {e}")

    def list_skills(self) -> list[HubSkill]:
        """List all skills in the hub."""
        index = self._fetch_index()
        return [HubSkill.from_dict(s) for s in index.get("skills", [])]

    def search(self, query: str) -> list[HubSkill]:
        """Search for skills by name, description, or tags.

        Supports multi-word queries by matching individual words.
        Results are ranked by number of matching words.
        """
        import re

        query_lower = query.lower()
        # Split query into individual words (at least 2 chars)
        query_words = [w for w in re.findall(r"\b[a-zA-Z]{2,}\b", query_lower)]
        skills = self.list_skills()

        results: list[tuple[int, HubSkill]] = []
        for skill in skills:
            # Build searchable text from skill fields
            skill_text = f"{skill.name} {skill.description} {' '.join(skill.tags)}".lower()
            skill_name_parts = skill.name.replace("-", " ").replace("_", " ").lower()

            # Score by number of matching words
            score = 0
            for word in query_words:
                if word in skill_text:
                    score += 1
                # Also match word stems in skill name (e.g., "review" matches "reviewer")
                elif any(word[:4] == part[:4] for part in skill_name_parts.split() if len(part) >= 4):
                    score += 1

            # Also check if full query matches (for exact phrase search)
            if query_lower in skill_text or query_lower in skill_name_parts:
                score += len(query_words)  # Boost for exact match

            if score > 0:
                results.append((score, skill))

        # Sort by score (descending) then by name
        results.sort(key=lambda x: (-x[0], x[1].name))
        return [skill for _, skill in results]

    def get_skill(self, name: str) -> Optional[HubSkill]:
        """Get a specific skill by name."""
        skills = self.list_skills()
        for skill in skills:
            if skill.name == name:
                return skill
        return None

    def download_skill(self, name: str, output_dir: Path) -> Path:
        """Download a skill to the specified directory."""
        skill = self.get_skill(name)
        if not skill:
            raise ValueError(f"Skill not found: {name}")

        skill_dir = output_dir / name
        skill_dir.mkdir(parents=True, exist_ok=True)

        # Download SKILL.md
        skill_md_url = f"{self.raw_url}/{name}/SKILL.md"
        try:
            with urllib.request.urlopen(skill_md_url, timeout=10) as response:
                content = response.read().decode("utf-8")
                (skill_dir / "SKILL.md").write_text(content)
        except urllib.error.URLError as e:
            raise ConnectionError(f"Failed to download skill: {e}")

        # Try to download optional files
        optional_files = ["tests.yml", "README.md", "STYLE_GUIDE.md"]
        for filename in optional_files:
            try:
                file_url = f"{self.raw_url}/{name}/{filename}"
                with urllib.request.urlopen(file_url, timeout=5) as response:
                    content = response.read().decode("utf-8")
                    (skill_dir / filename).write_text(content)
            except urllib.error.URLError:
                pass  # Optional file not found, skip

        return skill_dir


# Convenience functions
_client: Optional[HubClient] = None


def _get_client() -> HubClient:
    """Get or create the global hub client."""
    global _client
    if _client is None:
        _client = HubClient()
    return _client


def list_skills() -> list[HubSkill]:
    """List all skills in the hub."""
    return _get_client().list_skills()


def search_skills(query: str) -> list[HubSkill]:
    """Search for skills by name, description, or tags."""
    return _get_client().search(query)


def get_skill(name: str) -> Optional[HubSkill]:
    """Get a specific skill by name."""
    return _get_client().get_skill(name)


def install_skill(
    name: str,
    output_dir: Optional[Path] = None,
    project: bool = False,
) -> Path:
    """Install a skill from the hub.

    Args:
        name: Skill name to install
        output_dir: Custom output directory (overrides project flag)
        project: If True, install to ./.claude/skills/, else ~/.claude/skills/

    Returns:
        Path to the installed skill directory
    """
    from skillforge.claude_code import USER_SKILLS_DIR, PROJECT_SKILLS_DIR

    if output_dir:
        target_dir = output_dir
    elif project:
        target_dir = PROJECT_SKILLS_DIR
    else:
        target_dir = USER_SKILLS_DIR

    target_dir.mkdir(parents=True, exist_ok=True)

    return _get_client().download_skill(name, target_dir)
