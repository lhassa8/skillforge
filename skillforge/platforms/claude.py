"""Claude platform adapter for publishing skills.

This module provides the adapter for publishing SkillForge skills
to Anthropic's Claude platform (claude.ai and API).
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from skillforge.skill import Skill
from skillforge.platforms.base import (
    Platform,
    PlatformAdapter,
    PlatformCredentials,
    PublishError,
    PublishResult,
    TransformResult,
    register_adapter,
)


class ClaudeAdapter(PlatformAdapter):
    """Adapter for publishing skills to Claude.

    Supports:
    - Claude.ai Projects (upload as project knowledge)
    - Claude API (system prompts)
    - Claude Code (local installation)
    """

    @property
    def platform(self) -> Platform:
        return Platform.CLAUDE

    @property
    def platform_name(self) -> str:
        return "Claude (Anthropic)"

    @property
    def platform_description(self) -> str:
        return "Publish skills to Claude.ai Projects, API system prompts, or Claude Code"

    @property
    def supported_features(self) -> list[str]:
        return [
            "system_prompts",
            "project_knowledge",
            "local_installation",
            "mcp_tools",
            "artifacts",
        ]

    def transform(self, skill: Skill) -> TransformResult:
        """Transform skill for Claude platform.

        Generates:
        - System prompt format for API usage
        - Project knowledge format for claude.ai
        - SKILL.md format for Claude Code
        """
        warnings = []

        # Check for potential issues
        if len(skill.content) > 100000:
            warnings.append("Content exceeds 100K characters, may need truncation")

        if skill.description and len(skill.description) > 500:
            warnings.append("Description is long, consider shortening for better display")

        # Transform to Claude format
        content = {
            # System prompt format (for API)
            "system_prompt": self._to_system_prompt(skill),
            # Project knowledge format (for claude.ai)
            "project_knowledge": {
                "title": skill.name,
                "content": skill.to_skill_md(),
            },
            # Claude Code format
            "claude_code": {
                "skill_md": skill.to_skill_md(),
                "name": skill.name,
                "description": skill.description,
            },
        }

        metadata = {
            "char_count": len(skill.content),
            "has_version": skill.version is not None,
            "formats": ["system_prompt", "project_knowledge", "claude_code"],
        }

        return TransformResult(
            platform=Platform.CLAUDE,
            skill_name=skill.name,
            transformed_name=skill.name,
            content=content,
            metadata=metadata,
            warnings=warnings,
        )

    def _to_system_prompt(self, skill: Skill) -> str:
        """Convert skill to system prompt format."""
        parts = []

        # Add description as context
        if skill.description:
            parts.append(f"You have the following skill: {skill.description}")
            parts.append("")

        # Add skill content
        parts.append("Follow these instructions:")
        parts.append("")
        parts.append(skill.content)

        return "\n".join(parts)

    def publish(
        self,
        skill: Skill,
        credentials: PlatformCredentials,
        dry_run: bool = False,
    ) -> PublishResult:
        """Publish skill to Claude.

        Supports multiple publish modes:
        - api: Generate API-ready system prompt
        - project: Upload to claude.ai project (requires browser auth)
        - local: Install to Claude Code
        """
        # Validate credentials
        errors = self.validate_credentials(credentials)
        if errors:
            raise PublishError(f"Invalid credentials: {', '.join(errors)}")

        # Transform the skill
        transform_result = self.transform(skill)

        publish_mode = credentials.extra.get("mode", "local")

        if publish_mode == "local":
            return self._publish_local(skill, credentials, dry_run)
        elif publish_mode == "api":
            return self._publish_api(skill, credentials, transform_result, dry_run)
        elif publish_mode == "project":
            return self._publish_project(skill, credentials, transform_result, dry_run)
        else:
            raise PublishError(f"Unknown publish mode: {publish_mode}")

    def _publish_local(
        self,
        skill: Skill,
        credentials: PlatformCredentials,
        dry_run: bool,
    ) -> PublishResult:
        """Publish to local Claude Code installation."""
        from skillforge.claude_code import install_skill, get_skills_dir

        scope = "project" if credentials.extra.get("project", False) else "user"

        if dry_run:
            skills_dir = get_skills_dir(scope=scope)
            return PublishResult(
                platform=Platform.CLAUDE,
                skill_name=skill.name,
                published_id=f"local:{skill.name}",
                version=skill.version,
                url=str(skills_dir / skill.name),
                metadata={"mode": "local", "dry_run": True, "scope": scope},
            )

        # For local install, we need a skill directory (not just a Skill object)
        # If skill.path is not set, we need to handle this differently
        if skill.path is None:
            raise PublishError("Cannot install skill without a path. Use 'api' or 'project' mode.")

        result = install_skill(skill.path, scope=scope)

        return PublishResult(
            platform=Platform.CLAUDE,
            skill_name=skill.name,
            published_id=f"local:{skill.name}",
            version=skill.version,
            url=str(result.installed_path),
            metadata={
                "mode": "local",
                "scope": scope,
                "install_path": str(result.installed_path),
            },
        )

    def _publish_api(
        self,
        skill: Skill,
        credentials: PlatformCredentials,
        transform_result: TransformResult,
        dry_run: bool,
    ) -> PublishResult:
        """Generate API-ready configuration."""
        # For API mode, we just generate the configuration
        # Actual API calls would be made by the user's application

        output_dir = Path(credentials.extra.get("output_dir", "."))
        output_file = output_dir / f"{skill.name}_claude_api.json"

        api_config = {
            "model": credentials.extra.get("model", "claude-sonnet-4-20250514"),
            "system": transform_result.content["system_prompt"],
            "metadata": {
                "skill_name": skill.name,
                "skill_version": skill.version,
                "generated_at": datetime.now().isoformat(),
            },
        }

        if not dry_run:
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file.write_text(json.dumps(api_config, indent=2))

        return PublishResult(
            platform=Platform.CLAUDE,
            skill_name=skill.name,
            published_id=f"api:{skill.name}",
            version=skill.version,
            url=str(output_file),
            metadata={
                "mode": "api",
                "output_file": str(output_file),
                "model": api_config["model"],
            },
        )

    def _publish_project(
        self,
        skill: Skill,
        credentials: PlatformCredentials,
        transform_result: TransformResult,
        dry_run: bool,
    ) -> PublishResult:
        """Publish to claude.ai project.

        Note: This requires browser authentication and is not fully automated.
        We generate the content to upload manually.
        """
        output_dir = Path(credentials.extra.get("output_dir", "."))
        output_file = output_dir / f"{skill.name}_project_knowledge.md"

        if not dry_run:
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file.write_text(skill.to_skill_md())

        return PublishResult(
            platform=Platform.CLAUDE,
            skill_name=skill.name,
            published_id=f"project:{skill.name}",
            version=skill.version,
            url=str(output_file),
            metadata={
                "mode": "project",
                "output_file": str(output_file),
                "instructions": "Upload this file to your Claude.ai project as knowledge",
            },
        )

    def validate_credentials(self, credentials: PlatformCredentials) -> list[str]:
        """Validate Claude credentials."""
        errors = []

        if credentials.platform != Platform.CLAUDE:
            errors.append(f"Wrong platform: expected claude, got {credentials.platform.value}")

        mode = credentials.extra.get("mode", "local")

        if mode == "api":
            if not credentials.api_key:
                errors.append("API key required for API mode")
            elif not credentials.api_key.startswith("sk-ant-"):
                errors.append("Invalid API key format (should start with sk-ant-)")

        return errors


# Register the adapter
register_adapter(Platform.CLAUDE, ClaudeAdapter)
