"""Enterprise configuration for SkillForge.

This module provides configuration management for SkillForge including:
- Global and project-level configuration
- Enterprise settings (SSO, proxy, cloud storage)
- Environment variable overrides
- Configuration validation
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import yaml


# =============================================================================
# Configuration Paths
# =============================================================================

USER_CONFIG_DIR = Path.home() / ".config" / "skillforge"
USER_CONFIG_FILE = USER_CONFIG_DIR / "config.yml"
PROJECT_CONFIG_FILE = Path(".skillforge.yml")

# Environment variable prefix
ENV_PREFIX = "SKILLFORGE_"


class ConfigError(Exception):
    """Raised when configuration is invalid."""

    pass


# =============================================================================
# Configuration Enums
# =============================================================================


class AuthProvider(Enum):
    """Supported authentication providers."""

    NONE = "none"
    API_KEY = "api_key"
    OAUTH = "oauth"
    SSO_SAML = "sso_saml"
    SSO_OIDC = "sso_oidc"


class StorageBackend(Enum):
    """Supported storage backends."""

    LOCAL = "local"
    S3 = "s3"
    GCS = "gcs"
    AZURE_BLOB = "azure_blob"


class LogLevel(Enum):
    """Log levels."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


# =============================================================================
# Configuration Dataclasses
# =============================================================================


@dataclass
class ProxyConfig:
    """Proxy configuration for network requests.

    Attributes:
        http_proxy: HTTP proxy URL
        https_proxy: HTTPS proxy URL
        no_proxy: Comma-separated list of hosts to bypass proxy
        ssl_verify: Whether to verify SSL certificates
        ca_bundle: Path to custom CA bundle
    """

    http_proxy: Optional[str] = None
    https_proxy: Optional[str] = None
    no_proxy: Optional[str] = None
    ssl_verify: bool = True
    ca_bundle: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "http_proxy": self.http_proxy,
            "https_proxy": self.https_proxy,
            "no_proxy": self.no_proxy,
            "ssl_verify": self.ssl_verify,
            "ca_bundle": self.ca_bundle,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ProxyConfig:
        """Create from dictionary."""
        return cls(
            http_proxy=data.get("http_proxy"),
            https_proxy=data.get("https_proxy"),
            no_proxy=data.get("no_proxy"),
            ssl_verify=data.get("ssl_verify", True),
            ca_bundle=data.get("ca_bundle"),
        )

    @classmethod
    def from_env(cls) -> ProxyConfig:
        """Create from environment variables."""
        return cls(
            http_proxy=os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy"),
            https_proxy=os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy"),
            no_proxy=os.environ.get("NO_PROXY") or os.environ.get("no_proxy"),
            ssl_verify=os.environ.get("SSL_VERIFY", "true").lower() == "true",
            ca_bundle=os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE"),
        )


@dataclass
class AuthConfig:
    """Authentication configuration.

    Attributes:
        provider: Authentication provider type
        api_key: API key for API_KEY auth
        oauth_client_id: OAuth client ID
        oauth_client_secret: OAuth client secret
        sso_entity_id: SSO entity ID
        sso_metadata_url: SSO metadata URL
        sso_callback_url: SSO callback URL
    """

    provider: AuthProvider = AuthProvider.NONE
    api_key: Optional[str] = None
    oauth_client_id: Optional[str] = None
    oauth_client_secret: Optional[str] = None
    sso_entity_id: Optional[str] = None
    sso_metadata_url: Optional[str] = None
    sso_callback_url: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary (excluding secrets)."""
        return {
            "provider": self.provider.value,
            "oauth_client_id": self.oauth_client_id,
            "sso_entity_id": self.sso_entity_id,
            "sso_metadata_url": self.sso_metadata_url,
            "sso_callback_url": self.sso_callback_url,
            # Don't include secrets in serialization
        }

    @classmethod
    def from_dict(cls, data: dict) -> AuthConfig:
        """Create from dictionary."""
        provider = data.get("provider", "none")
        return cls(
            provider=AuthProvider(provider) if provider else AuthProvider.NONE,
            api_key=data.get("api_key"),
            oauth_client_id=data.get("oauth_client_id"),
            oauth_client_secret=data.get("oauth_client_secret"),
            sso_entity_id=data.get("sso_entity_id"),
            sso_metadata_url=data.get("sso_metadata_url"),
            sso_callback_url=data.get("sso_callback_url"),
        )


@dataclass
class StorageConfig:
    """Cloud storage configuration.

    Attributes:
        backend: Storage backend type
        local_path: Path for local storage
        bucket: Cloud storage bucket name
        prefix: Prefix/folder within bucket
        region: Cloud region
        endpoint_url: Custom endpoint URL (for S3-compatible)
        access_key: Access key ID
        secret_key: Secret access key
    """

    backend: StorageBackend = StorageBackend.LOCAL
    local_path: Optional[str] = None
    bucket: Optional[str] = None
    prefix: str = "skillforge/"
    region: Optional[str] = None
    endpoint_url: Optional[str] = None
    access_key: Optional[str] = None
    secret_key: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary (excluding secrets)."""
        return {
            "backend": self.backend.value,
            "local_path": self.local_path,
            "bucket": self.bucket,
            "prefix": self.prefix,
            "region": self.region,
            "endpoint_url": self.endpoint_url,
            # Don't include secrets
        }

    @classmethod
    def from_dict(cls, data: dict) -> StorageConfig:
        """Create from dictionary."""
        backend = data.get("backend", "local")
        return cls(
            backend=StorageBackend(backend) if backend else StorageBackend.LOCAL,
            local_path=data.get("local_path"),
            bucket=data.get("bucket"),
            prefix=data.get("prefix", "skillforge/"),
            region=data.get("region"),
            endpoint_url=data.get("endpoint_url"),
            access_key=data.get("access_key"),
            secret_key=data.get("secret_key"),
        )


@dataclass
class TelemetryConfig:
    """Telemetry and analytics configuration.

    Attributes:
        enabled: Whether telemetry is enabled
        anonymous: Whether to anonymize telemetry data
        endpoint: Custom telemetry endpoint
    """

    enabled: bool = False
    anonymous: bool = True
    endpoint: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "enabled": self.enabled,
            "anonymous": self.anonymous,
            "endpoint": self.endpoint,
        }

    @classmethod
    def from_dict(cls, data: dict) -> TelemetryConfig:
        """Create from dictionary."""
        return cls(
            enabled=data.get("enabled", False),
            anonymous=data.get("anonymous", True),
            endpoint=data.get("endpoint"),
        )


@dataclass
class SkillForgeConfig:
    """Main SkillForge configuration.

    Attributes:
        version: Configuration schema version
        default_model: Default AI model to use
        default_provider: Default AI provider
        skills_dir: Default skills directory
        cache_dir: Cache directory
        log_level: Logging level
        color_output: Whether to use colored output
        proxy: Proxy configuration
        auth: Authentication configuration
        storage: Storage configuration
        telemetry: Telemetry configuration
        custom: Custom configuration values
    """

    version: str = "1.0"
    default_model: str = "claude-sonnet-4-20250514"
    default_provider: str = "anthropic"
    skills_dir: Optional[str] = None
    cache_dir: Optional[str] = None
    log_level: LogLevel = LogLevel.INFO
    color_output: bool = True
    proxy: ProxyConfig = field(default_factory=ProxyConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    telemetry: TelemetryConfig = field(default_factory=TelemetryConfig)
    custom: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "version": self.version,
            "default_model": self.default_model,
            "default_provider": self.default_provider,
            "skills_dir": self.skills_dir,
            "cache_dir": self.cache_dir,
            "log_level": self.log_level.value,
            "color_output": self.color_output,
            "proxy": self.proxy.to_dict(),
            "auth": self.auth.to_dict(),
            "storage": self.storage.to_dict(),
            "telemetry": self.telemetry.to_dict(),
            "custom": self.custom,
        }

    @classmethod
    def from_dict(cls, data: dict) -> SkillForgeConfig:
        """Create from dictionary."""
        log_level = data.get("log_level", "info")
        return cls(
            version=data.get("version", "1.0"),
            default_model=data.get("default_model", "claude-sonnet-4-20250514"),
            default_provider=data.get("default_provider", "anthropic"),
            skills_dir=data.get("skills_dir"),
            cache_dir=data.get("cache_dir"),
            log_level=LogLevel(log_level) if log_level else LogLevel.INFO,
            color_output=data.get("color_output", True),
            proxy=ProxyConfig.from_dict(data.get("proxy", {})),
            auth=AuthConfig.from_dict(data.get("auth", {})),
            storage=StorageConfig.from_dict(data.get("storage", {})),
            telemetry=TelemetryConfig.from_dict(data.get("telemetry", {})),
            custom=data.get("custom", {}),
        )

    def to_yaml(self) -> str:
        """Convert to YAML string."""
        return yaml.dump(
            self.to_dict(),
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

    @classmethod
    def from_yaml(cls, yaml_str: str) -> SkillForgeConfig:
        """Create from YAML string."""
        data = yaml.safe_load(yaml_str) or {}
        return cls.from_dict(data)


# =============================================================================
# Configuration Loading
# =============================================================================


def get_config_dir() -> Path:
    """Get the user configuration directory, creating if needed."""
    USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return USER_CONFIG_DIR


def get_user_config_path() -> Path:
    """Get the path to user config file."""
    return USER_CONFIG_FILE


def get_project_config_path() -> Path:
    """Get the path to project config file."""
    return PROJECT_CONFIG_FILE.resolve()


def load_config_file(path: Path) -> dict:
    """Load configuration from a YAML file.

    Args:
        path: Path to configuration file

    Returns:
        Configuration dictionary

    Raises:
        ConfigError: If file cannot be loaded
    """
    if not path.exists():
        return {}

    try:
        with open(path) as f:
            return yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML in {path}: {e}")
    except OSError as e:
        raise ConfigError(f"Cannot read {path}: {e}")


def save_config_file(path: Path, config: dict) -> None:
    """Save configuration to a YAML file.

    Args:
        path: Path to configuration file
        config: Configuration dictionary
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(
            config,
            f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )


def load_env_overrides() -> dict:
    """Load configuration overrides from environment variables.

    Environment variables with SKILLFORGE_ prefix are converted to config keys.
    For example, SKILLFORGE_DEFAULT_MODEL becomes default_model.

    Returns:
        Dictionary of environment overrides
    """
    overrides = {}

    for key, value in os.environ.items():
        if key.startswith(ENV_PREFIX):
            config_key = key[len(ENV_PREFIX) :].lower()

            # Handle boolean values
            if value.lower() in ("true", "1", "yes"):
                value = True
            elif value.lower() in ("false", "0", "no"):
                value = False

            overrides[config_key] = value

    return overrides


def merge_configs(*configs: dict) -> dict:
    """Merge multiple configuration dictionaries.

    Later configs override earlier ones. Nested dicts are merged recursively.

    Args:
        *configs: Configuration dictionaries to merge

    Returns:
        Merged configuration
    """
    result: dict = {}

    for config in configs:
        for key, value in config.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = merge_configs(result[key], value)
            else:
                result[key] = value

    return result


# =============================================================================
# Global Configuration
# =============================================================================

_config: Optional[SkillForgeConfig] = None


def get_config(reload: bool = False) -> SkillForgeConfig:
    """Get the global SkillForge configuration.

    Loads configuration from (in order of precedence):
    1. Environment variables (highest)
    2. Project config (.skillforge.yml)
    3. User config (~/.config/skillforge/config.yml)
    4. Default values (lowest)

    Args:
        reload: Force reload of configuration

    Returns:
        SkillForgeConfig instance
    """
    global _config

    if _config is not None and not reload:
        return _config

    # Load configs in order of precedence (lowest to highest)
    user_config = load_config_file(get_user_config_path())
    project_config = load_config_file(get_project_config_path())
    env_overrides = load_env_overrides()

    # Merge configs
    merged = merge_configs(user_config, project_config, env_overrides)

    # Create config object
    _config = SkillForgeConfig.from_dict(merged)

    return _config


def set_config(config: SkillForgeConfig) -> None:
    """Set the global configuration.

    Args:
        config: Configuration to set
    """
    global _config
    _config = config


def reset_config() -> None:
    """Reset the global configuration to None (forces reload on next get)."""
    global _config
    _config = None


def save_user_config(config: SkillForgeConfig) -> Path:
    """Save configuration to user config file.

    Args:
        config: Configuration to save

    Returns:
        Path to saved config file
    """
    path = get_user_config_path()
    save_config_file(path, config.to_dict())
    return path


def save_project_config(config: SkillForgeConfig) -> Path:
    """Save configuration to project config file.

    Args:
        config: Configuration to save

    Returns:
        Path to saved config file
    """
    path = get_project_config_path()
    save_config_file(path, config.to_dict())
    return path


# =============================================================================
# Configuration Validation
# =============================================================================


def validate_config(config: SkillForgeConfig) -> list[str]:
    """Validate a configuration.

    Args:
        config: Configuration to validate

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    # Validate storage
    if config.storage.backend != StorageBackend.LOCAL:
        if not config.storage.bucket:
            errors.append(f"Storage bucket required for {config.storage.backend.value}")

    # Validate auth
    if config.auth.provider == AuthProvider.API_KEY:
        if not config.auth.api_key:
            errors.append("API key required for api_key auth provider")
    elif config.auth.provider == AuthProvider.OAUTH:
        if not config.auth.oauth_client_id:
            errors.append("OAuth client ID required for oauth auth provider")
    elif config.auth.provider in (AuthProvider.SSO_SAML, AuthProvider.SSO_OIDC):
        if not config.auth.sso_metadata_url:
            errors.append("SSO metadata URL required for SSO auth provider")

    # Validate proxy
    if config.proxy.ca_bundle and not Path(config.proxy.ca_bundle).exists():
        errors.append(f"CA bundle not found: {config.proxy.ca_bundle}")

    return errors


# =============================================================================
# Configuration Helpers
# =============================================================================


def get_skills_directory() -> Path:
    """Get the configured skills directory."""
    config = get_config()
    if config.skills_dir:
        return Path(config.skills_dir)
    return Path.home() / ".claude" / "skills"


def get_cache_directory() -> Path:
    """Get the configured cache directory."""
    config = get_config()
    if config.cache_dir:
        return Path(config.cache_dir)
    return USER_CONFIG_DIR / "cache"


def is_enterprise_mode() -> bool:
    """Check if running in enterprise mode (SSO enabled)."""
    config = get_config()
    return config.auth.provider in (AuthProvider.SSO_SAML, AuthProvider.SSO_OIDC)


def get_default_model() -> str:
    """Get the default AI model."""
    config = get_config()
    return config.default_model


def get_proxy_settings() -> dict[str, str]:
    """Get proxy settings as environment-style dict."""
    config = get_config()
    settings = {}

    if config.proxy.http_proxy:
        settings["http_proxy"] = config.proxy.http_proxy
        settings["HTTP_PROXY"] = config.proxy.http_proxy

    if config.proxy.https_proxy:
        settings["https_proxy"] = config.proxy.https_proxy
        settings["HTTPS_PROXY"] = config.proxy.https_proxy

    if config.proxy.no_proxy:
        settings["no_proxy"] = config.proxy.no_proxy
        settings["NO_PROXY"] = config.proxy.no_proxy

    return settings
