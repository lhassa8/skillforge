"""Base platform adapter for multi-platform publishing.

This module provides the abstract base class for platform adapters
that transform and publish skills to different AI platforms.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from skillforge.skill import Skill


class Platform(Enum):
    """Supported AI platforms."""

    CLAUDE = "claude"
    OPENAI = "openai"
    LANGCHAIN = "langchain"


class PublishError(Exception):
    """Raised when publishing fails."""

    pass


class TransformError(Exception):
    """Raised when skill transformation fails."""

    pass


@dataclass
class PlatformCredentials:
    """Credentials for platform authentication.

    Attributes:
        platform: Target platform
        api_key: API key for authentication
        organization_id: Optional organization ID
        project_id: Optional project ID
        extra: Additional platform-specific credentials
    """

    platform: Platform
    api_key: str
    organization_id: Optional[str] = None
    project_id: Optional[str] = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class TransformResult:
    """Result of transforming a skill for a platform.

    Attributes:
        platform: Target platform
        skill_name: Original skill name
        transformed_name: Name on target platform
        content: Transformed content/configuration
        metadata: Additional transformation metadata
        warnings: Any warnings during transformation
    """

    platform: Platform
    skill_name: str
    transformed_name: str
    content: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "platform": self.platform.value,
            "skill_name": self.skill_name,
            "transformed_name": self.transformed_name,
            "content": self.content,
            "metadata": self.metadata,
            "warnings": self.warnings,
        }


@dataclass
class PublishResult:
    """Result of publishing a skill to a platform.

    Attributes:
        platform: Target platform
        skill_name: Original skill name
        published_id: ID/URL on the platform
        published_at: When it was published
        version: Published version
        url: URL to access the published skill
        metadata: Additional publish metadata
    """

    platform: Platform
    skill_name: str
    published_id: str
    published_at: datetime = field(default_factory=datetime.now)
    version: Optional[str] = None
    url: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "platform": self.platform.value,
            "skill_name": self.skill_name,
            "published_id": self.published_id,
            "published_at": self.published_at.isoformat(),
            "version": self.version,
            "url": self.url,
            "metadata": self.metadata,
        }


class PlatformAdapter(ABC):
    """Abstract base class for platform adapters.

    Platform adapters transform SkillForge skills into platform-specific
    formats and handle publishing to those platforms.

    Subclasses must implement:
    - platform: The platform this adapter handles
    - transform(): Transform a skill for the platform
    - publish(): Publish a skill to the platform
    - validate_credentials(): Validate platform credentials
    """

    @property
    @abstractmethod
    def platform(self) -> Platform:
        """The platform this adapter handles."""
        pass

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Human-readable platform name."""
        pass

    @property
    @abstractmethod
    def platform_description(self) -> str:
        """Description of the platform."""
        pass

    @abstractmethod
    def transform(self, skill: Skill) -> TransformResult:
        """Transform a skill for this platform.

        Args:
            skill: The skill to transform

        Returns:
            TransformResult with platform-specific content

        Raises:
            TransformError: If transformation fails
        """
        pass

    @abstractmethod
    def publish(
        self,
        skill: Skill,
        credentials: PlatformCredentials,
        dry_run: bool = False,
    ) -> PublishResult:
        """Publish a skill to this platform.

        Args:
            skill: The skill to publish
            credentials: Platform credentials
            dry_run: If True, validate but don't actually publish

        Returns:
            PublishResult with publication details

        Raises:
            PublishError: If publishing fails
        """
        pass

    @abstractmethod
    def validate_credentials(self, credentials: PlatformCredentials) -> list[str]:
        """Validate platform credentials.

        Args:
            credentials: Credentials to validate

        Returns:
            List of validation errors (empty if valid)
        """
        pass

    def preview(self, skill: Skill) -> str:
        """Preview how a skill will appear on this platform.

        Args:
            skill: The skill to preview

        Returns:
            String representation of the transformed skill
        """
        result = self.transform(skill)
        import json

        return json.dumps(result.content, indent=2)

    def supports_feature(self, feature: str) -> bool:
        """Check if this platform supports a specific feature.

        Args:
            feature: Feature name to check

        Returns:
            True if feature is supported
        """
        return feature in self.supported_features

    @property
    def supported_features(self) -> list[str]:
        """List of features supported by this platform."""
        return []


# =============================================================================
# Platform Registry
# =============================================================================

_adapters: dict[Platform, type[PlatformAdapter]] = {}


def register_adapter(platform: Platform, adapter_class: type[PlatformAdapter]) -> None:
    """Register a platform adapter.

    Args:
        platform: Platform to register for
        adapter_class: Adapter class to register
    """
    _adapters[platform] = adapter_class


def get_adapter(platform: Platform) -> PlatformAdapter:
    """Get an adapter instance for a platform.

    Args:
        platform: Platform to get adapter for

    Returns:
        Adapter instance

    Raises:
        ValueError: If no adapter registered for platform
    """
    if platform not in _adapters:
        raise ValueError(f"No adapter registered for platform: {platform.value}")
    return _adapters[platform]()


def list_adapters() -> list[PlatformAdapter]:
    """List all registered platform adapters.

    Returns:
        List of adapter instances
    """
    return [adapter_class() for adapter_class in _adapters.values()]


def get_platform(name: str) -> Platform:
    """Get a Platform enum from string name.

    Args:
        name: Platform name string

    Returns:
        Platform enum value

    Raises:
        ValueError: If platform not found
    """
    try:
        return Platform(name.lower())
    except ValueError:
        valid = ", ".join(p.value for p in Platform)
        raise ValueError(f"Unknown platform: {name}. Valid platforms: {valid}")
