"""Multi-platform publishing for SkillForge skills.

This module provides adapters for publishing skills to various AI platforms:

- Claude (Anthropic) - claude.ai Projects, API, Claude Code
- OpenAI - Custom GPTs, API, Assistants
- LangChain - Prompt templates, Hub, Python modules

Example usage:

    from skillforge.platforms import (
        Platform,
        get_adapter,
        list_adapters,
        publish_skill,
        transform_skill,
    )

    # List available platforms
    for adapter in list_adapters():
        print(f"{adapter.platform_name}: {adapter.platform_description}")

    # Transform skill for a platform
    result = transform_skill("./skills/my-skill", Platform.OPENAI)
    print(result.content)

    # Publish to platform
    result = publish_skill(
        "./skills/my-skill",
        Platform.CLAUDE,
        mode="local",
    )
    print(f"Published: {result.published_id}")
"""

from skillforge.platforms.base import (
    Platform,
    PlatformAdapter,
    PlatformCredentials,
    PublishError,
    PublishResult,
    TransformError,
    TransformResult,
    get_adapter,
    get_platform,
    list_adapters,
    register_adapter,
)

# Import adapters to register them
from skillforge.platforms.claude import ClaudeAdapter
from skillforge.platforms.openai import OpenAIAdapter
from skillforge.platforms.langchain import LangChainAdapter

# Convenience imports
from pathlib import Path
from typing import Optional

from skillforge.skill import Skill


def transform_skill(
    skill_path: Path,
    platform: Platform,
) -> TransformResult:
    """Transform a skill for a platform.

    Args:
        skill_path: Path to skill directory
        platform: Target platform

    Returns:
        TransformResult with platform-specific content
    """
    skill = Skill.from_directory(skill_path)
    adapter = get_adapter(platform)
    return adapter.transform(skill)


def publish_skill(
    skill_path: Path,
    platform: Platform,
    api_key: Optional[str] = None,
    mode: Optional[str] = None,
    output_dir: Optional[Path] = None,
    dry_run: bool = False,
    **extra,
) -> PublishResult:
    """Publish a skill to a platform.

    Args:
        skill_path: Path to skill directory
        platform: Target platform
        api_key: API key for platform (if required)
        mode: Publish mode (platform-specific)
        output_dir: Output directory for generated files
        dry_run: If True, validate but don't publish
        **extra: Additional platform-specific options

    Returns:
        PublishResult with publication details
    """
    skill = Skill.from_directory(skill_path)
    adapter = get_adapter(platform)

    # Build credentials
    cred_extra = dict(extra)
    if mode:
        cred_extra["mode"] = mode
    if output_dir:
        cred_extra["output_dir"] = str(output_dir)

    credentials = PlatformCredentials(
        platform=platform,
        api_key=api_key or "",
        extra=cred_extra,
    )

    return adapter.publish(skill, credentials, dry_run=dry_run)


def publish_to_all(
    skill_path: Path,
    output_dir: Optional[Path] = None,
    dry_run: bool = False,
) -> dict[Platform, PublishResult]:
    """Publish a skill to all platforms.

    Args:
        skill_path: Path to skill directory
        output_dir: Output directory for generated files
        dry_run: If True, validate but don't publish

    Returns:
        Dictionary mapping platforms to their publish results
    """
    results = {}

    for adapter in list_adapters():
        try:
            result = publish_skill(
                skill_path=skill_path,
                platform=adapter.platform,
                output_dir=output_dir,
                dry_run=dry_run,
            )
            results[adapter.platform] = result
        except (PublishError, TransformError) as e:
            # Store error as metadata in a failed result
            results[adapter.platform] = PublishResult(
                platform=adapter.platform,
                skill_name=str(skill_path.name),
                published_id="error",
                metadata={"error": str(e)},
            )

    return results


def preview_for_platform(
    skill_path: Path,
    platform: Platform,
) -> str:
    """Preview how a skill will appear on a platform.

    Args:
        skill_path: Path to skill directory
        platform: Target platform

    Returns:
        String preview of the transformed skill
    """
    skill = Skill.from_directory(skill_path)
    adapter = get_adapter(platform)
    return adapter.preview(skill)


__all__ = [
    # Core types
    "Platform",
    "PlatformAdapter",
    "PlatformCredentials",
    "PublishError",
    "PublishResult",
    "TransformError",
    "TransformResult",
    # Registry
    "get_adapter",
    "get_platform",
    "list_adapters",
    "register_adapter",
    # Adapters
    "ClaudeAdapter",
    "OpenAIAdapter",
    "LangChainAdapter",
    # Convenience functions
    "transform_skill",
    "publish_skill",
    "publish_to_all",
    "preview_for_platform",
]
