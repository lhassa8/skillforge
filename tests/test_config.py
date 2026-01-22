"""Tests for skillforge.config module."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from skillforge.config import (
    # Enums
    AuthProvider,
    StorageBackend,
    LogLevel,
    # Dataclasses
    ProxyConfig,
    AuthConfig,
    StorageConfig,
    TelemetryConfig,
    SkillForgeConfig,
    # Constants
    USER_CONFIG_DIR,
    USER_CONFIG_FILE,
    PROJECT_CONFIG_FILE,
    ENV_PREFIX,
    ConfigError,
    # Functions
    get_config_dir,
    get_user_config_path,
    get_project_config_path,
    load_config_file,
    save_config_file,
    load_env_overrides,
    merge_configs,
    get_config,
    set_config,
    reset_config,
    save_user_config,
    validate_config,
    get_skills_directory,
    get_cache_directory,
    is_enterprise_mode,
    get_default_model,
    get_proxy_settings,
)


# =============================================================================
# Enum Tests
# =============================================================================


class TestAuthProvider:
    """Tests for AuthProvider enum."""

    def test_auth_provider_values(self):
        """Test enum values."""
        assert AuthProvider.NONE.value == "none"
        assert AuthProvider.API_KEY.value == "api_key"
        assert AuthProvider.OAUTH.value == "oauth"
        assert AuthProvider.SSO_SAML.value == "sso_saml"
        assert AuthProvider.SSO_OIDC.value == "sso_oidc"


class TestStorageBackend:
    """Tests for StorageBackend enum."""

    def test_storage_backend_values(self):
        """Test enum values."""
        assert StorageBackend.LOCAL.value == "local"
        assert StorageBackend.S3.value == "s3"
        assert StorageBackend.GCS.value == "gcs"
        assert StorageBackend.AZURE_BLOB.value == "azure_blob"


class TestLogLevel:
    """Tests for LogLevel enum."""

    def test_log_level_values(self):
        """Test enum values."""
        assert LogLevel.DEBUG.value == "debug"
        assert LogLevel.INFO.value == "info"
        assert LogLevel.WARNING.value == "warning"
        assert LogLevel.ERROR.value == "error"


# =============================================================================
# ProxyConfig Tests
# =============================================================================


class TestProxyConfig:
    """Tests for ProxyConfig dataclass."""

    def test_default_values(self):
        """Test default values."""
        config = ProxyConfig()
        assert config.http_proxy is None
        assert config.https_proxy is None
        assert config.no_proxy is None
        assert config.ssl_verify is True
        assert config.ca_bundle is None

    def test_with_values(self):
        """Test with custom values."""
        config = ProxyConfig(
            http_proxy="http://proxy:8080",
            https_proxy="https://proxy:8443",
            no_proxy="localhost,127.0.0.1",
            ssl_verify=False,
            ca_bundle="/path/to/ca.crt",
        )
        assert config.http_proxy == "http://proxy:8080"
        assert config.https_proxy == "https://proxy:8443"
        assert config.ssl_verify is False

    def test_to_dict(self):
        """Test conversion to dictionary."""
        config = ProxyConfig(http_proxy="http://proxy:8080")
        data = config.to_dict()
        assert data["http_proxy"] == "http://proxy:8080"
        assert data["ssl_verify"] is True

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "http_proxy": "http://proxy:8080",
            "ssl_verify": False,
        }
        config = ProxyConfig.from_dict(data)
        assert config.http_proxy == "http://proxy:8080"
        assert config.ssl_verify is False

    def test_from_env(self):
        """Test creation from environment."""
        with patch.dict(os.environ, {"HTTP_PROXY": "http://env-proxy:8080"}):
            config = ProxyConfig.from_env()
            assert config.http_proxy == "http://env-proxy:8080"


# =============================================================================
# AuthConfig Tests
# =============================================================================


class TestAuthConfig:
    """Tests for AuthConfig dataclass."""

    def test_default_values(self):
        """Test default values."""
        config = AuthConfig()
        assert config.provider == AuthProvider.NONE
        assert config.api_key is None

    def test_with_api_key(self):
        """Test with API key auth."""
        config = AuthConfig(
            provider=AuthProvider.API_KEY,
            api_key="test-key",
        )
        assert config.provider == AuthProvider.API_KEY
        assert config.api_key == "test-key"

    def test_to_dict_excludes_secrets(self):
        """Test that to_dict doesn't include secrets."""
        config = AuthConfig(
            provider=AuthProvider.API_KEY,
            api_key="secret-key",
        )
        data = config.to_dict()
        assert "api_key" not in data
        assert data["provider"] == "api_key"

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "provider": "oauth",
            "oauth_client_id": "client-123",
        }
        config = AuthConfig.from_dict(data)
        assert config.provider == AuthProvider.OAUTH
        assert config.oauth_client_id == "client-123"


# =============================================================================
# StorageConfig Tests
# =============================================================================


class TestStorageConfig:
    """Tests for StorageConfig dataclass."""

    def test_default_values(self):
        """Test default values."""
        config = StorageConfig()
        assert config.backend == StorageBackend.LOCAL
        assert config.prefix == "skillforge/"

    def test_s3_config(self):
        """Test S3 configuration."""
        config = StorageConfig(
            backend=StorageBackend.S3,
            bucket="my-bucket",
            region="us-east-1",
        )
        assert config.backend == StorageBackend.S3
        assert config.bucket == "my-bucket"

    def test_to_dict_excludes_secrets(self):
        """Test that to_dict doesn't include secrets."""
        config = StorageConfig(
            backend=StorageBackend.S3,
            bucket="my-bucket",
            access_key="AKIAIOSFODNN7EXAMPLE",
            secret_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        )
        data = config.to_dict()
        assert "access_key" not in data
        assert "secret_key" not in data


# =============================================================================
# TelemetryConfig Tests
# =============================================================================


class TestTelemetryConfig:
    """Tests for TelemetryConfig dataclass."""

    def test_default_values(self):
        """Test default values."""
        config = TelemetryConfig()
        assert config.enabled is False
        assert config.anonymous is True

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {"enabled": True, "anonymous": False}
        config = TelemetryConfig.from_dict(data)
        assert config.enabled is True
        assert config.anonymous is False


# =============================================================================
# SkillForgeConfig Tests
# =============================================================================


class TestSkillForgeConfig:
    """Tests for SkillForgeConfig dataclass."""

    def test_default_values(self):
        """Test default values."""
        config = SkillForgeConfig()
        assert config.version == "1.0"
        assert config.default_model == "claude-sonnet-4-20250514"
        assert config.default_provider == "anthropic"
        assert config.log_level == LogLevel.INFO
        assert config.color_output is True

    def test_to_dict(self):
        """Test conversion to dictionary."""
        config = SkillForgeConfig()
        data = config.to_dict()
        assert data["version"] == "1.0"
        assert data["default_model"] == "claude-sonnet-4-20250514"
        assert "proxy" in data
        assert "auth" in data
        assert "storage" in data

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "default_model": "gpt-4o",
            "log_level": "debug",
        }
        config = SkillForgeConfig.from_dict(data)
        assert config.default_model == "gpt-4o"
        assert config.log_level == LogLevel.DEBUG

    def test_to_yaml(self):
        """Test YAML serialization."""
        config = SkillForgeConfig()
        yaml_str = config.to_yaml()
        assert "version:" in yaml_str
        assert "default_model:" in yaml_str

    def test_from_yaml(self):
        """Test YAML deserialization."""
        yaml_str = """
version: "1.0"
default_model: gpt-4o
log_level: warning
"""
        config = SkillForgeConfig.from_yaml(yaml_str)
        assert config.default_model == "gpt-4o"
        assert config.log_level == LogLevel.WARNING


# =============================================================================
# Config File Operations
# =============================================================================


class TestConfigFileOperations:
    """Tests for config file operations."""

    def test_load_config_file_missing(self, tmp_path: Path):
        """Test loading non-existent file returns empty dict."""
        path = tmp_path / "missing.yml"
        result = load_config_file(path)
        assert result == {}

    def test_load_config_file(self, tmp_path: Path):
        """Test loading config file."""
        path = tmp_path / "config.yml"
        path.write_text("default_model: gpt-4o\nlog_level: debug")

        result = load_config_file(path)
        assert result["default_model"] == "gpt-4o"
        assert result["log_level"] == "debug"

    def test_load_config_file_invalid_yaml(self, tmp_path: Path):
        """Test loading invalid YAML raises error."""
        path = tmp_path / "invalid.yml"
        path.write_text("invalid: yaml: content:")

        with pytest.raises(ConfigError, match="Invalid YAML"):
            load_config_file(path)

    def test_save_config_file(self, tmp_path: Path):
        """Test saving config file."""
        path = tmp_path / "config.yml"
        config = {"default_model": "test-model", "version": "1.0"}

        save_config_file(path, config)

        assert path.exists()
        loaded = yaml.safe_load(path.read_text())
        assert loaded["default_model"] == "test-model"

    def test_save_config_file_creates_dirs(self, tmp_path: Path):
        """Test saving creates parent directories."""
        path = tmp_path / "subdir" / "config.yml"
        save_config_file(path, {"key": "value"})
        assert path.exists()


# =============================================================================
# Environment Overrides
# =============================================================================


class TestEnvironmentOverrides:
    """Tests for environment variable overrides."""

    def test_load_env_overrides_empty(self):
        """Test with no SKILLFORGE_ variables."""
        with patch.dict(os.environ, {}, clear=True):
            result = load_env_overrides()
            assert result == {}

    def test_load_env_overrides(self):
        """Test loading environment overrides."""
        env = {
            "SKILLFORGE_DEFAULT_MODEL": "env-model",
            "SKILLFORGE_LOG_LEVEL": "debug",
            "OTHER_VAR": "ignored",
        }
        with patch.dict(os.environ, env, clear=True):
            result = load_env_overrides()
            assert result["default_model"] == "env-model"
            assert result["log_level"] == "debug"
            assert "other_var" not in result

    def test_load_env_overrides_boolean(self):
        """Test boolean parsing in env overrides."""
        env = {
            "SKILLFORGE_COLOR_OUTPUT": "false",
            "SKILLFORGE_TELEMETRY_ENABLED": "true",
        }
        with patch.dict(os.environ, env, clear=True):
            result = load_env_overrides()
            assert result["color_output"] is False
            assert result["telemetry_enabled"] is True


# =============================================================================
# Config Merging
# =============================================================================


class TestConfigMerging:
    """Tests for config merging."""

    def test_merge_simple(self):
        """Test merging simple configs."""
        a = {"key1": "value1"}
        b = {"key2": "value2"}
        result = merge_configs(a, b)
        assert result == {"key1": "value1", "key2": "value2"}

    def test_merge_override(self):
        """Test later configs override earlier."""
        a = {"key": "old"}
        b = {"key": "new"}
        result = merge_configs(a, b)
        assert result["key"] == "new"

    def test_merge_nested(self):
        """Test merging nested dicts."""
        a = {"outer": {"inner1": "a"}}
        b = {"outer": {"inner2": "b"}}
        result = merge_configs(a, b)
        assert result["outer"]["inner1"] == "a"
        assert result["outer"]["inner2"] == "b"


# =============================================================================
# Global Config
# =============================================================================


class TestGlobalConfig:
    """Tests for global config functions."""

    def test_get_config(self):
        """Test getting global config."""
        reset_config()
        config = get_config()
        assert isinstance(config, SkillForgeConfig)

    def test_set_config(self):
        """Test setting global config."""
        custom = SkillForgeConfig(default_model="custom-model")
        set_config(custom)

        config = get_config()
        assert config.default_model == "custom-model"

        reset_config()

    def test_reset_config(self):
        """Test resetting global config."""
        custom = SkillForgeConfig(default_model="custom")
        set_config(custom)
        reset_config()

        config = get_config()
        assert config.default_model == "claude-sonnet-4-20250514"


# =============================================================================
# Config Validation
# =============================================================================


class TestConfigValidation:
    """Tests for config validation."""

    def test_validate_valid_config(self):
        """Test validating a valid config."""
        config = SkillForgeConfig()
        errors = validate_config(config)
        assert errors == []

    def test_validate_s3_without_bucket(self):
        """Test S3 backend requires bucket."""
        config = SkillForgeConfig(
            storage=StorageConfig(backend=StorageBackend.S3)
        )
        errors = validate_config(config)
        assert any("bucket" in e.lower() for e in errors)

    def test_validate_api_key_auth_without_key(self):
        """Test API key auth requires key."""
        config = SkillForgeConfig(
            auth=AuthConfig(provider=AuthProvider.API_KEY)
        )
        errors = validate_config(config)
        assert any("api key" in e.lower() for e in errors)


# =============================================================================
# Helper Functions
# =============================================================================


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_skills_directory_default(self):
        """Test default skills directory."""
        reset_config()
        path = get_skills_directory()
        assert path == Path.home() / ".claude" / "skills"

    def test_get_skills_directory_custom(self):
        """Test custom skills directory."""
        config = SkillForgeConfig(skills_dir="/custom/skills")
        set_config(config)

        path = get_skills_directory()
        assert path == Path("/custom/skills")

        reset_config()

    def test_is_enterprise_mode_false(self):
        """Test enterprise mode detection (false)."""
        reset_config()
        assert is_enterprise_mode() is False

    def test_is_enterprise_mode_sso(self):
        """Test enterprise mode with SSO."""
        config = SkillForgeConfig(
            auth=AuthConfig(provider=AuthProvider.SSO_SAML)
        )
        set_config(config)

        assert is_enterprise_mode() is True

        reset_config()

    def test_get_default_model(self):
        """Test getting default model."""
        reset_config()
        model = get_default_model()
        assert model == "claude-sonnet-4-20250514"

    def test_get_proxy_settings_empty(self):
        """Test proxy settings with no proxy."""
        reset_config()
        settings = get_proxy_settings()
        assert settings == {}

    def test_get_proxy_settings(self):
        """Test proxy settings with proxy configured."""
        config = SkillForgeConfig(
            proxy=ProxyConfig(http_proxy="http://proxy:8080")
        )
        set_config(config)

        settings = get_proxy_settings()
        assert settings["http_proxy"] == "http://proxy:8080"
        assert settings["HTTP_PROXY"] == "http://proxy:8080"

        reset_config()
