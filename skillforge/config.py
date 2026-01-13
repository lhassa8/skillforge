"""Configuration management for SkillForge."""

from pathlib import Path
from typing import Any

import yaml

# Default configuration directory
CONFIG_DIR = Path.home() / ".skillforge"
CONFIG_FILE = CONFIG_DIR / "config.yaml"
RECORDINGS_DIR = CONFIG_DIR / "recordings"
LOGS_DIR = CONFIG_DIR / "logs"
CACHE_DIR = CONFIG_DIR / "cache"

# Default configuration values
DEFAULT_CONFIG: dict[str, Any] = {
    "default_sandbox_root": str(CONFIG_DIR / "sandboxes"),
    "max_log_kb_per_command": 256,
    "redact_patterns": [
        r"AKIA[0-9A-Z]{16}",  # AWS access key
        r"Bearer\s+[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+",  # JWT Bearer token
        r"password\s*=\s*['\"]?[^'\"\s]+",  # password=...
        r"token\s*=\s*['\"]?[^'\"\s]+",  # token=...
        r"apikey\s*=\s*['\"]?[^'\"\s]+",  # apikey=...
        r"api_key\s*=\s*['\"]?[^'\"\s]+",  # api_key=...
    ],
    "ignore_paths": [
        "__pycache__",
        "*.pyc",
        ".DS_Store",
        "node_modules",
        ".venv",
        "venv",
    ],
    "default_shell": "bash",
}


def get_config_dir() -> Path:
    """Return the SkillForge configuration directory path."""
    return CONFIG_DIR


def get_config_file() -> Path:
    """Return the SkillForge configuration file path."""
    return CONFIG_FILE


def config_exists() -> bool:
    """Check if the configuration directory and file exist."""
    return CONFIG_DIR.exists() and CONFIG_FILE.exists()


def load_config() -> dict[str, Any]:
    """Load configuration from file, or return defaults if not found."""
    if not CONFIG_FILE.exists():
        return DEFAULT_CONFIG.copy()

    with open(CONFIG_FILE, "r") as f:
        user_config = yaml.safe_load(f) or {}

    # Merge with defaults (user config takes precedence)
    config = DEFAULT_CONFIG.copy()
    config.update(user_config)
    return config


def save_config(config: dict[str, Any]) -> None:
    """Save configuration to file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    with open(CONFIG_FILE, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)


def init_config_dir() -> Path:
    """Initialize the configuration directory with default config and subdirectories.

    Returns the path to the configuration directory.
    """
    # Create main config directory
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    RECORDINGS_DIR.mkdir(exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)
    CACHE_DIR.mkdir(exist_ok=True)

    # Create default config file if it doesn't exist
    if not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG)

    return CONFIG_DIR
