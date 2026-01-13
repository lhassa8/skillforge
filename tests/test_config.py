"""Tests for the configuration module."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from skillforge import config


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create a temporary config directory for testing."""
    config_dir = tmp_path / ".skillforge"
    with patch.object(config, "CONFIG_DIR", config_dir):
        with patch.object(config, "CONFIG_FILE", config_dir / "config.yaml"):
            with patch.object(config, "RECORDINGS_DIR", config_dir / "recordings"):
                with patch.object(config, "LOGS_DIR", config_dir / "logs"):
                    with patch.object(config, "CACHE_DIR", config_dir / "cache"):
                        yield config_dir


def test_default_config_has_required_keys():
    """Test that default config contains all required keys."""
    required_keys = [
        "default_sandbox_root",
        "max_log_kb_per_command",
        "redact_patterns",
        "ignore_paths",
        "default_shell",
    ]
    for key in required_keys:
        assert key in config.DEFAULT_CONFIG


def test_config_exists_returns_false_when_missing(temp_config_dir):
    """Test config_exists returns False when directory doesn't exist."""
    assert not config.config_exists()


def test_init_config_dir_creates_structure(temp_config_dir):
    """Test that init_config_dir creates all necessary directories and files."""
    result = config.init_config_dir()

    assert result == temp_config_dir
    assert temp_config_dir.exists()
    assert (temp_config_dir / "config.yaml").exists()
    assert (temp_config_dir / "recordings").exists()
    assert (temp_config_dir / "logs").exists()
    assert (temp_config_dir / "cache").exists()


def test_init_config_dir_creates_valid_yaml(temp_config_dir):
    """Test that the created config file is valid YAML."""
    config.init_config_dir()

    config_file = temp_config_dir / "config.yaml"
    with open(config_file) as f:
        loaded = yaml.safe_load(f)

    assert loaded is not None
    assert "default_sandbox_root" in loaded
    assert "default_shell" in loaded


def test_load_config_returns_defaults_when_missing(temp_config_dir):
    """Test that load_config returns defaults when file doesn't exist."""
    loaded = config.load_config()
    assert loaded == config.DEFAULT_CONFIG


def test_load_config_merges_with_defaults(temp_config_dir):
    """Test that load_config merges user config with defaults."""
    # Create config dir and custom config
    temp_config_dir.mkdir(parents=True)
    config_file = temp_config_dir / "config.yaml"

    custom_config = {"default_shell": "zsh", "custom_key": "custom_value"}
    with open(config_file, "w") as f:
        yaml.dump(custom_config, f)

    loaded = config.load_config()

    # Custom values should override defaults
    assert loaded["default_shell"] == "zsh"
    assert loaded["custom_key"] == "custom_value"
    # Defaults should still be present
    assert "max_log_kb_per_command" in loaded


def test_save_config_creates_file(temp_config_dir):
    """Test that save_config creates the config file."""
    test_config = {"test_key": "test_value"}
    config.save_config(test_config)

    config_file = temp_config_dir / "config.yaml"
    assert config_file.exists()

    with open(config_file) as f:
        loaded = yaml.safe_load(f)

    assert loaded["test_key"] == "test_value"


def test_config_exists_returns_true_after_init(temp_config_dir):
    """Test config_exists returns True after initialization."""
    config.init_config_dir()
    assert config.config_exists()
