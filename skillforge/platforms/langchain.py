"""LangChain platform adapter for publishing skills.

This module provides the adapter for publishing SkillForge skills
to LangChain-compatible formats including prompt templates and chains.
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


class LangChainAdapter(PlatformAdapter):
    """Adapter for publishing skills to LangChain.

    Supports:
    - Prompt templates
    - Chat prompt templates
    - LangChain Hub
    - Python module generation
    """

    @property
    def platform(self) -> Platform:
        return Platform.LANGCHAIN

    @property
    def platform_name(self) -> str:
        return "LangChain"

    @property
    def platform_description(self) -> str:
        return "Publish skills as LangChain prompt templates, chains, or to LangChain Hub"

    @property
    def supported_features(self) -> list[str]:
        return [
            "prompt_templates",
            "chat_prompt_templates",
            "langchain_hub",
            "python_module",
            "chains",
        ]

    def transform(self, skill: Skill) -> TransformResult:
        """Transform skill for LangChain platform.

        Generates:
        - Prompt template format
        - Chat prompt template format
        - Python module code
        """
        warnings = []

        # Extract variables from skill content
        variables = self._extract_variables(skill.content)

        if not variables:
            warnings.append("No input variables detected, adding default 'input' variable")
            variables = ["input"]

        # Transform to LangChain formats
        content = {
            # Prompt template format
            "prompt_template": self._to_prompt_template(skill, variables),
            # Chat prompt template format
            "chat_prompt_template": self._to_chat_prompt_template(skill, variables),
            # Python module
            "python_module": self._to_python_module(skill, variables),
            # LangChain Hub format
            "hub_format": self._to_hub_format(skill, variables),
        }

        metadata = {
            "variables": variables,
            "char_count": len(skill.content),
            "formats": ["prompt_template", "chat_prompt_template", "python_module", "hub_format"],
        }

        return TransformResult(
            platform=Platform.LANGCHAIN,
            skill_name=skill.name,
            transformed_name=skill.name.replace("-", "_"),
            content=content,
            metadata=metadata,
            warnings=warnings,
        )

    def _extract_variables(self, content: str) -> list[str]:
        """Extract potential input variables from skill content."""
        import re

        variables = set()

        # Look for common placeholder patterns
        # {variable}, {{variable}}, <variable>, [variable]
        patterns = [
            r"\{(\w+)\}",  # {var}
            r"\{\{(\w+)\}\}",  # {{var}}
            r"<(\w+)>",  # <var>
            r"\[(\w+)\]",  # [var]
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content)
            variables.update(matches)

        # Filter out common non-variables
        non_variables = {
            "code", "example", "note", "warning", "tip",
            "python", "javascript", "bash", "json", "yaml",
        }
        variables = variables - non_variables

        return sorted(list(variables))

    def _to_prompt_template(self, skill: Skill, variables: list[str]) -> dict:
        """Convert skill to LangChain PromptTemplate format."""
        # Normalize placeholders to LangChain format {variable}
        template = skill.content

        return {
            "template": template,
            "input_variables": variables,
            "template_format": "f-string",
            "metadata": {
                "name": skill.name,
                "description": skill.description,
                "version": skill.version,
            },
        }

    def _to_chat_prompt_template(self, skill: Skill, variables: list[str]) -> dict:
        """Convert skill to LangChain ChatPromptTemplate format."""
        return {
            "messages": [
                {
                    "role": "system",
                    "content": f"You are an AI assistant. {skill.description or ''}",
                },
                {
                    "role": "human",
                    "content": skill.content,
                },
            ],
            "input_variables": variables,
            "metadata": {
                "name": skill.name,
                "description": skill.description,
                "version": skill.version,
            },
        }

    def _to_python_module(self, skill: Skill, variables: list[str]) -> str:
        """Generate Python module code for LangChain usage."""
        class_name = "".join(word.title() for word in skill.name.split("-"))

        # Escape content for Python string
        escaped_content = skill.content.replace('"""', '\\"\\"\\"').replace("\\", "\\\\")

        code = f'''"""LangChain prompt template for {skill.name}.

{skill.description or 'Auto-generated from SkillForge skill.'}

Generated by SkillForge v0.12.0
"""

from langchain_core.prompts import ChatPromptTemplate, PromptTemplate


# Skill metadata
SKILL_NAME = "{skill.name}"
SKILL_DESCRIPTION = """{skill.description or ''}"""
SKILL_VERSION = "{skill.version or '1.0.0'}"

# Template content
TEMPLATE = """
{escaped_content}
"""

# Input variables
INPUT_VARIABLES = {variables}


def get_prompt_template() -> PromptTemplate:
    """Get a PromptTemplate for this skill."""
    return PromptTemplate(
        template=TEMPLATE,
        input_variables=INPUT_VARIABLES,
    )


def get_chat_prompt_template() -> ChatPromptTemplate:
    """Get a ChatPromptTemplate for this skill."""
    return ChatPromptTemplate.from_messages([
        ("system", SKILL_DESCRIPTION),
        ("human", TEMPLATE),
    ])


class {class_name}Prompt:
    """Prompt class for {skill.name} skill."""

    name = SKILL_NAME
    description = SKILL_DESCRIPTION
    version = SKILL_VERSION
    input_variables = INPUT_VARIABLES

    @classmethod
    def get_template(cls) -> PromptTemplate:
        """Get the prompt template."""
        return get_prompt_template()

    @classmethod
    def get_chat_template(cls) -> ChatPromptTemplate:
        """Get the chat prompt template."""
        return get_chat_prompt_template()

    @classmethod
    def format(cls, **kwargs) -> str:
        """Format the template with given variables."""
        return get_prompt_template().format(**kwargs)
'''
        return code

    def _to_hub_format(self, skill: Skill, variables: list[str]) -> dict:
        """Convert skill to LangChain Hub format."""
        return {
            "name": skill.name,
            "description": skill.description,
            "template": skill.content,
            "input_variables": variables,
            "tags": ["skillforge", "auto-generated"],
            "metadata": {
                "source": "skillforge",
                "version": skill.version,
            },
        }

    def publish(
        self,
        skill: Skill,
        credentials: PlatformCredentials,
        dry_run: bool = False,
    ) -> PublishResult:
        """Publish skill to LangChain.

        Supports multiple publish modes:
        - module: Generate Python module
        - hub: Push to LangChain Hub
        - json: Export as JSON configuration
        """
        errors = self.validate_credentials(credentials)
        if errors:
            raise PublishError(f"Invalid credentials: {', '.join(errors)}")

        transform_result = self.transform(skill)

        publish_mode = credentials.extra.get("mode", "module")

        if publish_mode == "module":
            return self._publish_module(skill, credentials, transform_result, dry_run)
        elif publish_mode == "json":
            return self._publish_json(skill, credentials, transform_result, dry_run)
        elif publish_mode == "hub":
            return self._publish_hub(skill, credentials, transform_result, dry_run)
        else:
            raise PublishError(f"Unknown publish mode: {publish_mode}")

    def _publish_module(
        self,
        skill: Skill,
        credentials: PlatformCredentials,
        transform_result: TransformResult,
        dry_run: bool,
    ) -> PublishResult:
        """Generate Python module file."""
        output_dir = Path(credentials.extra.get("output_dir", "."))
        module_name = skill.name.replace("-", "_")
        output_file = output_dir / f"{module_name}_prompt.py"

        if not dry_run:
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file.write_text(transform_result.content["python_module"])

        return PublishResult(
            platform=Platform.LANGCHAIN,
            skill_name=skill.name,
            published_id=f"module:{module_name}",
            version=skill.version,
            url=str(output_file),
            metadata={
                "mode": "module",
                "output_file": str(output_file),
                "module_name": module_name,
                "variables": transform_result.metadata["variables"],
            },
        )

    def _publish_json(
        self,
        skill: Skill,
        credentials: PlatformCredentials,
        transform_result: TransformResult,
        dry_run: bool,
    ) -> PublishResult:
        """Export as JSON configuration."""
        output_dir = Path(credentials.extra.get("output_dir", "."))
        output_file = output_dir / f"{skill.name}_langchain.json"

        config = {
            "prompt_template": transform_result.content["prompt_template"],
            "chat_prompt_template": transform_result.content["chat_prompt_template"],
            "metadata": {
                "skill_name": skill.name,
                "skill_version": skill.version,
                "generated_at": datetime.now().isoformat(),
                "generated_by": "skillforge",
            },
        }

        if not dry_run:
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file.write_text(json.dumps(config, indent=2))

        return PublishResult(
            platform=Platform.LANGCHAIN,
            skill_name=skill.name,
            published_id=f"json:{skill.name}",
            version=skill.version,
            url=str(output_file),
            metadata={
                "mode": "json",
                "output_file": str(output_file),
            },
        )

    def _publish_hub(
        self,
        skill: Skill,
        credentials: PlatformCredentials,
        transform_result: TransformResult,
        dry_run: bool,
    ) -> PublishResult:
        """Push to LangChain Hub."""
        if dry_run:
            return PublishResult(
                platform=Platform.LANGCHAIN,
                skill_name=skill.name,
                published_id=f"hub:dry_run:{skill.name}",
                version=skill.version,
                metadata={
                    "mode": "hub",
                    "dry_run": True,
                    "would_push": transform_result.content["hub_format"],
                },
            )

        # For actual Hub push, we'd need langchain-hub package
        try:
            from langchain import hub
            from langchain_core.prompts import PromptTemplate

            # Create the prompt
            template_config = transform_result.content["prompt_template"]
            prompt = PromptTemplate(
                template=template_config["template"],
                input_variables=template_config["input_variables"],
            )

            # Push to hub
            repo_name = credentials.extra.get("repo", skill.name)
            owner = credentials.extra.get("owner", "skillforge")

            hub.push(f"{owner}/{repo_name}", prompt, api_key=credentials.api_key)

            hub_url = f"https://smith.langchain.com/hub/{owner}/{repo_name}"

            return PublishResult(
                platform=Platform.LANGCHAIN,
                skill_name=skill.name,
                published_id=f"{owner}/{repo_name}",
                version=skill.version,
                url=hub_url,
                metadata={
                    "mode": "hub",
                    "repo": repo_name,
                    "owner": owner,
                },
            )

        except ImportError:
            raise PublishError(
                "LangChain Hub package required. "
                "Install with: pip install langchain-hub"
            )
        except Exception as e:
            raise PublishError(f"Failed to push to Hub: {e}")

    def validate_credentials(self, credentials: PlatformCredentials) -> list[str]:
        """Validate LangChain credentials."""
        errors = []

        if credentials.platform != Platform.LANGCHAIN:
            errors.append(f"Wrong platform: expected langchain, got {credentials.platform.value}")

        mode = credentials.extra.get("mode", "module")

        if mode == "hub":
            if not credentials.api_key:
                errors.append("LangSmith API key required for Hub mode")

        return errors


# Register the adapter
register_adapter(Platform.LANGCHAIN, LangChainAdapter)
