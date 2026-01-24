"""OpenAI platform adapter for publishing skills as Custom GPTs.

This module provides the adapter for publishing SkillForge skills
to OpenAI as Custom GPTs or API system prompts.
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


class OpenAIAdapter(PlatformAdapter):
    """Adapter for publishing skills to OpenAI.

    Supports:
    - Custom GPTs (GPT Builder format)
    - API system prompts
    - Assistants API
    """

    @property
    def platform(self) -> Platform:
        return Platform.OPENAI

    @property
    def platform_name(self) -> str:
        return "OpenAI (GPTs & API)"

    @property
    def platform_description(self) -> str:
        return "Publish skills as Custom GPTs, API system prompts, or Assistants"

    @property
    def supported_features(self) -> list[str]:
        return [
            "custom_gpts",
            "system_prompts",
            "assistants_api",
            "function_calling",
            "code_interpreter",
            "file_search",
        ]

    def transform(self, skill: Skill) -> TransformResult:
        """Transform skill for OpenAI platform.

        Generates:
        - Custom GPT configuration
        - API system prompt
        - Assistants API configuration
        """
        warnings = []

        # OpenAI has a system prompt limit (~8000 tokens typical)
        if len(skill.content) > 32000:
            warnings.append("Content is very long, may exceed token limits")

        # Check for features that need adaptation
        if "```" in skill.content:
            warnings.append("Code blocks will be preserved but formatting may differ")

        # Transform to OpenAI formats
        content = {
            # Custom GPT format
            "custom_gpt": self._to_custom_gpt(skill),
            # API system prompt
            "system_prompt": self._to_system_prompt(skill),
            # Assistants API format
            "assistant": self._to_assistant(skill),
        }

        metadata = {
            "char_count": len(skill.content),
            "estimated_tokens": len(skill.content) // 4,  # Rough estimate
            "formats": ["custom_gpt", "system_prompt", "assistant"],
        }

        return TransformResult(
            platform=Platform.OPENAI,
            skill_name=skill.name,
            transformed_name=self._to_gpt_name(skill.name),
            content=content,
            metadata=metadata,
            warnings=warnings,
        )

    def _to_gpt_name(self, name: str) -> str:
        """Convert skill name to GPT-friendly name."""
        # Convert kebab-case to Title Case
        return name.replace("-", " ").replace("_", " ").title()

    def _to_system_prompt(self, skill: Skill) -> str:
        """Convert skill to OpenAI system prompt format."""
        parts = []

        # Add role/context
        parts.append(f"You are an AI assistant with expertise in: {skill.description}")
        parts.append("")

        # Add instructions
        parts.append("## Instructions")
        parts.append("")
        parts.append(skill.content)

        return "\n".join(parts)

    def _to_custom_gpt(self, skill: Skill) -> dict:
        """Convert skill to Custom GPT configuration."""
        return {
            "name": self._to_gpt_name(skill.name),
            "description": skill.description or f"A GPT powered by {skill.name}",
            "instructions": self._to_system_prompt(skill),
            "conversation_starters": self._generate_conversation_starters(skill),
            "capabilities": {
                "web_browsing": False,
                "code_interpreter": "code" in skill.content.lower(),
                "dalle_image_generation": False,
                "file_upload": True,
            },
        }

    def _to_assistant(self, skill: Skill) -> dict:
        """Convert skill to Assistants API format."""
        tools = []

        # Add code interpreter if skill mentions code
        if any(kw in skill.content.lower() for kw in ["code", "script", "program", "execute"]):
            tools.append({"type": "code_interpreter"})

        # Add file search if skill mentions files/documents
        if any(kw in skill.content.lower() for kw in ["file", "document", "search", "find"]):
            tools.append({"type": "file_search"})

        return {
            "name": self._to_gpt_name(skill.name),
            "description": skill.description,
            "instructions": self._to_system_prompt(skill),
            "model": "gpt-4o",
            "tools": tools,
            "metadata": {
                "source": "skillforge",
                "skill_name": skill.name,
                "skill_version": skill.version,
            },
        }

    def _generate_conversation_starters(self, skill: Skill) -> list[str]:
        """Generate conversation starters based on skill content."""
        starters = []

        # Generic starters based on description
        if skill.description:
            starters.append(f"Help me with {skill.description.lower()}")

        # Add some generic starters
        starters.extend([
            "What can you help me with?",
            "How do I get started?",
            "Show me an example",
        ])

        return starters[:4]  # GPTs support up to 4 starters

    def publish(
        self,
        skill: Skill,
        credentials: PlatformCredentials,
        dry_run: bool = False,
    ) -> PublishResult:
        """Publish skill to OpenAI.

        Supports multiple publish modes:
        - gpt: Generate Custom GPT configuration
        - api: Generate API-ready system prompt
        - assistant: Create via Assistants API
        """
        errors = self.validate_credentials(credentials)
        if errors:
            raise PublishError(f"Invalid credentials: {', '.join(errors)}")

        transform_result = self.transform(skill)

        publish_mode = credentials.extra.get("mode", "gpt")

        if publish_mode == "gpt":
            return self._publish_gpt(skill, credentials, transform_result, dry_run)
        elif publish_mode == "api":
            return self._publish_api(skill, credentials, transform_result, dry_run)
        elif publish_mode == "assistant":
            return self._publish_assistant(skill, credentials, transform_result, dry_run)
        else:
            raise PublishError(f"Unknown publish mode: {publish_mode}")

    def _publish_gpt(
        self,
        skill: Skill,
        credentials: PlatformCredentials,
        transform_result: TransformResult,
        dry_run: bool,
    ) -> PublishResult:
        """Generate Custom GPT configuration."""
        output_dir = Path(credentials.extra.get("output_dir", "."))
        output_file = output_dir / f"{skill.name}_custom_gpt.json"

        gpt_config = transform_result.content["custom_gpt"]
        gpt_config["metadata"] = {
            "skill_name": skill.name,
            "skill_version": skill.version,
            "generated_at": datetime.now().isoformat(),
            "generated_by": "skillforge",
        }

        if not dry_run:
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file.write_text(json.dumps(gpt_config, indent=2))

        return PublishResult(
            platform=Platform.OPENAI,
            skill_name=skill.name,
            published_id=f"gpt:{skill.name}",
            version=skill.version,
            url=str(output_file),
            metadata={
                "mode": "gpt",
                "output_file": str(output_file),
                "gpt_name": gpt_config["name"],
                "instructions": "Import this configuration in GPT Builder at chat.openai.com",
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
        output_dir = Path(credentials.extra.get("output_dir", "."))
        output_file = output_dir / f"{skill.name}_openai_api.json"

        api_config = {
            "model": credentials.extra.get("model", "gpt-4o"),
            "messages": [
                {
                    "role": "system",
                    "content": transform_result.content["system_prompt"],
                }
            ],
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
            platform=Platform.OPENAI,
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

    def _publish_assistant(
        self,
        skill: Skill,
        credentials: PlatformCredentials,
        transform_result: TransformResult,
        dry_run: bool,
    ) -> PublishResult:
        """Create an Assistant via the API."""
        if dry_run:
            return PublishResult(
                platform=Platform.OPENAI,
                skill_name=skill.name,
                published_id=f"assistant:dry_run:{skill.name}",
                version=skill.version,
                metadata={
                    "mode": "assistant",
                    "dry_run": True,
                    "would_create": transform_result.content["assistant"],
                },
            )

        # For actual creation, we'd need the openai package
        try:
            import openai

            client = openai.OpenAI(api_key=credentials.api_key)

            assistant_config = transform_result.content["assistant"]
            assistant = client.beta.assistants.create(
                name=assistant_config["name"],
                description=assistant_config["description"],
                instructions=assistant_config["instructions"],
                model=assistant_config["model"],
                tools=assistant_config["tools"],
                metadata=assistant_config["metadata"],
            )

            return PublishResult(
                platform=Platform.OPENAI,
                skill_name=skill.name,
                published_id=assistant.id,
                version=skill.version,
                url=f"https://platform.openai.com/assistants/{assistant.id}",
                metadata={
                    "mode": "assistant",
                    "assistant_id": assistant.id,
                    "model": assistant_config["model"],
                },
            )

        except ImportError:
            raise PublishError(
                "OpenAI package required for assistant mode. "
                "Install with: pip install openai"
            )
        except Exception as e:
            raise PublishError(f"Failed to create assistant: {e}")

    def validate_credentials(self, credentials: PlatformCredentials) -> list[str]:
        """Validate OpenAI credentials."""
        errors = []

        if credentials.platform != Platform.OPENAI:
            errors.append(f"Wrong platform: expected openai, got {credentials.platform.value}")

        mode = credentials.extra.get("mode", "gpt")

        if mode == "assistant":
            if not credentials.api_key:
                errors.append("API key required for assistant mode")
            elif not credentials.api_key.startswith("sk-"):
                errors.append("Invalid API key format (should start with sk-)")

        return errors


# Register the adapter
register_adapter(Platform.OPENAI, OpenAIAdapter)
