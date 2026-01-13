"""Secrets management for SkillForge.

This module provides secure storage and retrieval of secrets for use in skills.
Supports multiple backends:
- Environment variables
- Encrypted local file storage
- HashiCorp Vault (optional)
- AWS Secrets Manager (optional)

Secrets are referenced in skills using {secret:name} syntax.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import yaml

from skillforge.config import CONFIG_DIR


# =============================================================================
# Constants
# =============================================================================

SECRETS_DIR = CONFIG_DIR / "secrets"
SECRETS_FILE = SECRETS_DIR / "secrets.enc"
SECRETS_KEY_FILE = SECRETS_DIR / ".key"
SECRETS_METADATA_FILE = SECRETS_DIR / "metadata.yaml"

# Pattern to match secret placeholders: {secret:name}
SECRET_PLACEHOLDER_PATTERN = re.compile(r"\{secret:([a-zA-Z_][a-zA-Z0-9_]*)\}")

# Characters to mask secrets in logs
MASK_CHAR = "*"
MASK_LENGTH = 8


# =============================================================================
# Exceptions
# =============================================================================


class SecretsError(Exception):
    """Base exception for secrets operations."""
    pass


class SecretNotFoundError(SecretsError):
    """Raised when a secret is not found."""
    pass


class SecretBackendError(SecretsError):
    """Raised when a backend operation fails."""
    pass


class EncryptionError(SecretsError):
    """Raised when encryption/decryption fails."""
    pass


# =============================================================================
# Encryption Utilities
# =============================================================================


def _get_or_create_key() -> bytes:
    """Get or create the encryption key.

    Returns:
        32-byte encryption key
    """
    SECRETS_DIR.mkdir(parents=True, exist_ok=True)

    if SECRETS_KEY_FILE.exists():
        return base64.b64decode(SECRETS_KEY_FILE.read_text().strip())

    # Generate new key
    key = os.urandom(32)
    SECRETS_KEY_FILE.write_text(base64.b64encode(key).decode())
    # Restrict permissions
    SECRETS_KEY_FILE.chmod(0o600)
    return key


def _derive_key(password: str, salt: bytes) -> bytes:
    """Derive encryption key from password using PBKDF2.

    Args:
        password: User password
        salt: Random salt

    Returns:
        32-byte derived key
    """
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000, dklen=32)


def _simple_encrypt(data: bytes, key: bytes) -> bytes:
    """Simple XOR-based encryption (for portability without cryptography package).

    For production use, install cryptography package for Fernet encryption.

    Args:
        data: Data to encrypt
        key: 32-byte encryption key

    Returns:
        Encrypted data with IV prepended
    """
    # Generate random IV
    iv = os.urandom(16)

    # Extend key with IV for XOR
    key_stream = hashlib.sha256(key + iv).digest()
    while len(key_stream) < len(data):
        key_stream += hashlib.sha256(key_stream).digest()

    # XOR encryption
    encrypted = bytes(a ^ b for a, b in zip(data, key_stream[:len(data)]))

    return iv + encrypted


def _simple_decrypt(encrypted_data: bytes, key: bytes) -> bytes:
    """Simple XOR-based decryption.

    Args:
        encrypted_data: Encrypted data with IV prepended
        key: 32-byte encryption key

    Returns:
        Decrypted data
    """
    if len(encrypted_data) < 16:
        raise EncryptionError("Invalid encrypted data")

    iv = encrypted_data[:16]
    data = encrypted_data[16:]

    # Recreate key stream
    key_stream = hashlib.sha256(key + iv).digest()
    while len(key_stream) < len(data):
        key_stream += hashlib.sha256(key_stream).digest()

    # XOR decryption
    decrypted = bytes(a ^ b for a, b in zip(data, key_stream[:len(data)]))

    return decrypted


def encrypt_value(value: str, key: Optional[bytes] = None) -> str:
    """Encrypt a secret value.

    Args:
        value: Plain text value
        key: Encryption key (uses stored key if not provided)

    Returns:
        Base64-encoded encrypted value
    """
    if key is None:
        key = _get_or_create_key()

    try:
        # Try to use cryptography package if available
        from cryptography.fernet import Fernet
        fernet_key = base64.urlsafe_b64encode(key)
        f = Fernet(fernet_key)
        encrypted = f.encrypt(value.encode())
        return "fernet:" + encrypted.decode()
    except ImportError:
        # Fall back to simple encryption
        encrypted = _simple_encrypt(value.encode(), key)
        return "simple:" + base64.b64encode(encrypted).decode()


def decrypt_value(encrypted_value: str, key: Optional[bytes] = None) -> str:
    """Decrypt a secret value.

    Args:
        encrypted_value: Base64-encoded encrypted value
        key: Encryption key (uses stored key if not provided)

    Returns:
        Decrypted plain text value
    """
    if key is None:
        key = _get_or_create_key()

    if encrypted_value.startswith("fernet:"):
        try:
            from cryptography.fernet import Fernet
            fernet_key = base64.urlsafe_b64encode(key)
            f = Fernet(fernet_key)
            return f.decrypt(encrypted_value[7:].encode()).decode()
        except ImportError:
            raise EncryptionError(
                "Secret was encrypted with Fernet but cryptography package is not installed. "
                "Run: pip install cryptography"
            )
    elif encrypted_value.startswith("simple:"):
        encrypted_bytes = base64.b64decode(encrypted_value[7:])
        return _simple_decrypt(encrypted_bytes, key).decode()
    else:
        # Legacy or plain value
        return encrypted_value


# =============================================================================
# Secret Backend Interface
# =============================================================================


@dataclass
class SecretInfo:
    """Information about a secret (without the actual value)."""

    name: str
    backend: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    description: str = ""


class SecretBackend(ABC):
    """Abstract base class for secret backends."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Backend name."""
        pass

    @abstractmethod
    def get(self, name: str) -> str:
        """Get a secret value.

        Args:
            name: Secret name

        Returns:
            Secret value

        Raises:
            SecretNotFoundError: If secret doesn't exist
        """
        pass

    @abstractmethod
    def set(self, name: str, value: str, description: str = "") -> None:
        """Set a secret value.

        Args:
            name: Secret name
            value: Secret value
            description: Optional description
        """
        pass

    @abstractmethod
    def delete(self, name: str) -> bool:
        """Delete a secret.

        Args:
            name: Secret name

        Returns:
            True if deleted, False if didn't exist
        """
        pass

    @abstractmethod
    def list(self) -> list[SecretInfo]:
        """List all secrets (names only, not values).

        Returns:
            List of SecretInfo objects
        """
        pass

    @abstractmethod
    def exists(self, name: str) -> bool:
        """Check if a secret exists.

        Args:
            name: Secret name

        Returns:
            True if exists
        """
        pass


# =============================================================================
# Environment Variable Backend
# =============================================================================


class EnvSecretBackend(SecretBackend):
    """Secret backend using environment variables.

    Secrets are read from environment variables with a configurable prefix.
    This backend is read-only (cannot set/delete secrets).
    """

    def __init__(self, prefix: str = "SKILLFORGE_SECRET_"):
        self._prefix = prefix

    @property
    def name(self) -> str:
        return "env"

    def get(self, name: str) -> str:
        env_name = self._prefix + name.upper()
        value = os.environ.get(env_name)
        if value is None:
            raise SecretNotFoundError(f"Environment variable not found: {env_name}")
        return value

    def set(self, name: str, value: str, description: str = "") -> None:
        raise SecretBackendError(
            "Environment backend is read-only. "
            "Set secrets using environment variables directly."
        )

    def delete(self, name: str) -> bool:
        raise SecretBackendError("Environment backend is read-only.")

    def list(self) -> list[SecretInfo]:
        secrets = []
        for key in os.environ:
            if key.startswith(self._prefix):
                secret_name = key[len(self._prefix):].lower()
                secrets.append(SecretInfo(
                    name=secret_name,
                    backend=self.name,
                ))
        return secrets

    def exists(self, name: str) -> bool:
        env_name = self._prefix + name.upper()
        return env_name in os.environ


# =============================================================================
# Encrypted File Backend
# =============================================================================


class FileSecretBackend(SecretBackend):
    """Secret backend using encrypted local file storage.

    Secrets are stored in an encrypted JSON file with metadata in a
    separate YAML file.
    """

    def __init__(
        self,
        secrets_file: Optional[Path] = None,
        metadata_file: Optional[Path] = None,
    ):
        self._secrets_file = secrets_file or SECRETS_FILE
        self._metadata_file = metadata_file or SECRETS_METADATA_FILE
        self._secrets: dict[str, str] = {}
        self._metadata: dict[str, dict[str, Any]] = {}
        self._load()

    @property
    def name(self) -> str:
        return "file"

    def _load(self) -> None:
        """Load secrets from disk."""
        if self._secrets_file.exists():
            try:
                encrypted_data = self._secrets_file.read_text()
                if encrypted_data.strip():
                    decrypted = decrypt_value(encrypted_data)
                    self._secrets = json.loads(decrypted)
            except (json.JSONDecodeError, EncryptionError):
                self._secrets = {}

        if self._metadata_file.exists():
            try:
                self._metadata = yaml.safe_load(self._metadata_file.read_text()) or {}
            except yaml.YAMLError:
                self._metadata = {}

    def _save(self) -> None:
        """Save secrets to disk."""
        SECRETS_DIR.mkdir(parents=True, exist_ok=True)

        # Save encrypted secrets
        secrets_json = json.dumps(self._secrets)
        encrypted = encrypt_value(secrets_json)
        self._secrets_file.write_text(encrypted)
        self._secrets_file.chmod(0o600)

        # Save metadata
        self._metadata_file.write_text(yaml.dump(self._metadata, default_flow_style=False))

    def get(self, name: str) -> str:
        if name not in self._secrets:
            raise SecretNotFoundError(f"Secret not found: {name}")
        return self._secrets[name]

    def set(self, name: str, value: str, description: str = "") -> None:
        now = datetime.now().isoformat()

        is_new = name not in self._secrets
        self._secrets[name] = value

        if name not in self._metadata:
            self._metadata[name] = {}

        if is_new:
            self._metadata[name]["created_at"] = now

        self._metadata[name]["updated_at"] = now
        if description:
            self._metadata[name]["description"] = description

        self._save()

    def delete(self, name: str) -> bool:
        if name not in self._secrets:
            return False

        del self._secrets[name]
        self._metadata.pop(name, None)
        self._save()
        return True

    def list(self) -> list[SecretInfo]:
        secrets = []
        for name in self._secrets:
            meta = self._metadata.get(name, {})
            secrets.append(SecretInfo(
                name=name,
                backend=self.name,
                created_at=meta.get("created_at"),
                updated_at=meta.get("updated_at"),
                description=meta.get("description", ""),
            ))
        return secrets

    def exists(self, name: str) -> bool:
        return name in self._secrets


# =============================================================================
# Vault Backend (Optional)
# =============================================================================


class VaultSecretBackend(SecretBackend):
    """Secret backend using HashiCorp Vault.

    Requires VAULT_ADDR and VAULT_TOKEN environment variables.
    """

    def __init__(
        self,
        addr: Optional[str] = None,
        token: Optional[str] = None,
        mount_point: str = "secret",
        path_prefix: str = "skillforge/",
    ):
        self._addr = addr or os.environ.get("VAULT_ADDR", "http://localhost:8200")
        self._token = token or os.environ.get("VAULT_TOKEN")
        self._mount_point = mount_point
        self._path_prefix = path_prefix

        if not self._token:
            raise SecretBackendError(
                "Vault token not found. Set VAULT_TOKEN environment variable."
            )

    @property
    def name(self) -> str:
        return "vault"

    def _request(
        self,
        method: str,
        path: str,
        data: Optional[dict] = None,
    ) -> Optional[dict]:
        """Make a request to Vault API."""
        try:
            import httpx
        except ImportError:
            raise SecretBackendError(
                "httpx package required for Vault. Run: pip install httpx"
            )

        url = f"{self._addr}/v1/{self._mount_point}/data/{self._path_prefix}{path}"
        headers = {"X-Vault-Token": self._token}

        try:
            if method == "GET":
                response = httpx.get(url, headers=headers, timeout=10.0)
            elif method == "POST":
                response = httpx.post(url, headers=headers, json={"data": data}, timeout=10.0)
            elif method == "DELETE":
                # For KV v2, we need to delete metadata
                meta_url = f"{self._addr}/v1/{self._mount_point}/metadata/{self._path_prefix}{path}"
                response = httpx.delete(meta_url, headers=headers, timeout=10.0)
            else:
                raise SecretBackendError(f"Unknown method: {method}")

            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json() if response.content else {}

        except Exception as e:
            raise SecretBackendError(f"Vault request failed: {e}")

    def get(self, name: str) -> str:
        result = self._request("GET", name)
        if not result or "data" not in result:
            raise SecretNotFoundError(f"Secret not found in Vault: {name}")

        data = result.get("data", {}).get("data", {})
        if "value" not in data:
            raise SecretNotFoundError(f"Secret has no value: {name}")

        return data["value"]

    def set(self, name: str, value: str, description: str = "") -> None:
        data = {"value": value}
        if description:
            data["description"] = description
        self._request("POST", name, data)

    def delete(self, name: str) -> bool:
        try:
            self._request("DELETE", name)
            return True
        except SecretBackendError:
            return False

    def list(self) -> list[SecretInfo]:
        """List secrets (requires list capability on path)."""
        try:
            import httpx
        except ImportError:
            return []

        url = f"{self._addr}/v1/{self._mount_point}/metadata/{self._path_prefix}"
        headers = {"X-Vault-Token": self._token}

        try:
            response = httpx.request("LIST", url, headers=headers, timeout=10.0)
            if response.status_code == 404:
                return []
            response.raise_for_status()

            data = response.json()
            keys = data.get("data", {}).get("keys", [])

            return [
                SecretInfo(name=key.rstrip("/"), backend=self.name)
                for key in keys
            ]
        except Exception:
            return []

    def exists(self, name: str) -> bool:
        result = self._request("GET", name)
        return result is not None and "data" in result


# =============================================================================
# Secret Manager
# =============================================================================


class SecretManager:
    """Manages secrets across multiple backends.

    Backends are checked in order until a secret is found.
    """

    def __init__(self, backends: Optional[list[SecretBackend]] = None):
        if backends is None:
            # Default backends: env first, then file
            self._backends = [
                EnvSecretBackend(),
                FileSecretBackend(),
            ]
        else:
            self._backends = backends

    def add_backend(self, backend: SecretBackend, priority: int = -1) -> None:
        """Add a backend at specified priority (index).

        Args:
            backend: Backend to add
            priority: Index to insert at (-1 = end)
        """
        if priority < 0:
            self._backends.append(backend)
        else:
            self._backends.insert(priority, backend)

    def get(self, name: str) -> str:
        """Get a secret from any backend.

        Args:
            name: Secret name

        Returns:
            Secret value

        Raises:
            SecretNotFoundError: If not found in any backend
        """
        errors = []
        for backend in self._backends:
            try:
                return backend.get(name)
            except SecretNotFoundError:
                continue
            except SecretBackendError as e:
                errors.append(f"{backend.name}: {e}")

        if errors:
            raise SecretNotFoundError(
                f"Secret not found: {name}. Backend errors: {'; '.join(errors)}"
            )
        raise SecretNotFoundError(f"Secret not found in any backend: {name}")

    def set(self, name: str, value: str, description: str = "", backend_name: str = "file") -> None:
        """Set a secret in a specific backend.

        Args:
            name: Secret name
            value: Secret value
            description: Optional description
            backend_name: Backend to use (default: file)
        """
        for backend in self._backends:
            if backend.name == backend_name:
                backend.set(name, value, description)
                return

        raise SecretBackendError(f"Backend not found: {backend_name}")

    def delete(self, name: str, backend_name: Optional[str] = None) -> bool:
        """Delete a secret.

        Args:
            name: Secret name
            backend_name: Specific backend (None = try all writable backends)

        Returns:
            True if deleted
        """
        if backend_name:
            for backend in self._backends:
                if backend.name == backend_name:
                    return backend.delete(name)
            return False

        # Try all writable backends
        for backend in self._backends:
            try:
                if backend.delete(name):
                    return True
            except SecretBackendError:
                continue

        return False

    def list(self, backend_name: Optional[str] = None) -> list[SecretInfo]:
        """List all secrets.

        Args:
            backend_name: Specific backend (None = all backends)

        Returns:
            List of SecretInfo objects
        """
        if backend_name:
            for backend in self._backends:
                if backend.name == backend_name:
                    return backend.list()
            return []

        # Merge from all backends
        secrets = []
        seen = set()
        for backend in self._backends:
            for secret in backend.list():
                if secret.name not in seen:
                    secrets.append(secret)
                    seen.add(secret.name)

        return secrets

    def exists(self, name: str) -> bool:
        """Check if a secret exists in any backend.

        Args:
            name: Secret name

        Returns:
            True if exists
        """
        for backend in self._backends:
            try:
                if backend.exists(name):
                    return True
            except SecretBackendError:
                continue
        return False

    def get_backend_names(self) -> list[str]:
        """Get list of configured backend names."""
        return [b.name for b in self._backends]


# =============================================================================
# Secret Placeholder Resolution
# =============================================================================


def extract_secret_placeholders(text: str) -> list[str]:
    """Extract secret placeholder names from text.

    Args:
        text: Text that may contain {secret:name} placeholders

    Returns:
        List of secret names referenced
    """
    return SECRET_PLACEHOLDER_PATTERN.findall(text)


def resolve_secrets(
    text: str,
    manager: Optional[SecretManager] = None,
) -> str:
    """Resolve secret placeholders in text.

    Args:
        text: Text containing {secret:name} placeholders
        manager: SecretManager to use (creates default if not provided)

    Returns:
        Text with secrets resolved

    Raises:
        SecretNotFoundError: If a required secret is not found
    """
    if manager is None:
        manager = SecretManager()

    def replace(match: re.Match) -> str:
        name = match.group(1)
        return manager.get(name)

    return SECRET_PLACEHOLDER_PATTERN.sub(replace, text)


def resolve_secrets_in_dict(
    data: dict[str, Any],
    manager: Optional[SecretManager] = None,
) -> dict[str, Any]:
    """Recursively resolve secret placeholders in a dictionary.

    Args:
        data: Dictionary that may contain secret placeholders
        manager: SecretManager to use

    Returns:
        Dictionary with secrets resolved
    """
    if manager is None:
        manager = SecretManager()

    return _resolve_value(data, manager)


def _resolve_value(value: Any, manager: SecretManager) -> Any:
    """Recursively resolve secrets in any value type."""
    if isinstance(value, str):
        return resolve_secrets(value, manager)
    elif isinstance(value, dict):
        return {k: _resolve_value(v, manager) for k, v in value.items()}
    elif isinstance(value, list):
        return [_resolve_value(item, manager) for item in value]
    else:
        return value


# =============================================================================
# Secret Masking for Logs
# =============================================================================


class SecretMasker:
    """Masks secret values in text for safe logging.

    Maintains a set of secret values to mask and replaces them with asterisks.
    """

    def __init__(self):
        self._secrets: set[str] = set()
        self._min_length = 4  # Don't mask very short values (too many false positives)

    def add_secret(self, value: str) -> None:
        """Add a secret value to mask.

        Args:
            value: Secret value to mask
        """
        if value and len(value) >= self._min_length:
            self._secrets.add(value)

    def add_secrets(self, values: list[str]) -> None:
        """Add multiple secret values to mask.

        Args:
            values: Secret values to mask
        """
        for value in values:
            self.add_secret(value)

    def add_from_manager(self, manager: SecretManager) -> None:
        """Add all secrets from a manager.

        Args:
            manager: SecretManager to get secrets from
        """
        for secret_info in manager.list():
            try:
                value = manager.get(secret_info.name)
                self.add_secret(value)
            except (SecretNotFoundError, SecretBackendError):
                continue

    def mask(self, text: str) -> str:
        """Mask secret values in text.

        Args:
            text: Text that may contain secret values

        Returns:
            Text with secret values replaced by asterisks
        """
        result = text
        for secret in self._secrets:
            if secret in result:
                masked = MASK_CHAR * MASK_LENGTH
                result = result.replace(secret, masked)
        return result

    def mask_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        """Mask secret values in a dictionary.

        Args:
            data: Dictionary that may contain secret values

        Returns:
            Dictionary with secrets masked
        """
        return self._mask_value(data)

    def _mask_value(self, value: Any) -> Any:
        """Recursively mask secrets in any value type."""
        if isinstance(value, str):
            return self.mask(value)
        elif isinstance(value, dict):
            return {k: self._mask_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._mask_value(item) for item in value]
        else:
            return value

    def clear(self) -> None:
        """Clear all tracked secrets."""
        self._secrets.clear()


# =============================================================================
# Global Secret Manager Instance
# =============================================================================

_global_manager: Optional[SecretManager] = None
_global_masker: Optional[SecretMasker] = None


def get_secret_manager() -> SecretManager:
    """Get the global secret manager instance."""
    global _global_manager
    if _global_manager is None:
        _global_manager = SecretManager()
    return _global_manager


def get_secret_masker() -> SecretMasker:
    """Get the global secret masker instance."""
    global _global_masker
    if _global_masker is None:
        _global_masker = SecretMasker()
        _global_masker.add_from_manager(get_secret_manager())
    return _global_masker


def reset_globals() -> None:
    """Reset global instances (mainly for testing)."""
    global _global_manager, _global_masker
    _global_manager = None
    _global_masker = None


# =============================================================================
# Utility Functions
# =============================================================================


def init_secrets_dir() -> Path:
    """Initialize the secrets directory structure.

    Returns:
        Path to secrets directory
    """
    SECRETS_DIR.mkdir(parents=True, exist_ok=True)
    return SECRETS_DIR


def mask_in_command(command: str, manager: Optional[SecretManager] = None) -> str:
    """Mask any secrets that appear in a command string.

    Args:
        command: Command that may contain secrets
        manager: SecretManager to get secret values from

    Returns:
        Command with secret values masked
    """
    if manager is None:
        manager = get_secret_manager()

    masker = SecretMasker()
    masker.add_from_manager(manager)
    return masker.mask(command)


def get_secret(name: str) -> str:
    """Convenience function to get a secret from the global manager.

    Args:
        name: Secret name

    Returns:
        Secret value
    """
    return get_secret_manager().get(name)


def set_secret(name: str, value: str, description: str = "") -> None:
    """Convenience function to set a secret in the global manager.

    Args:
        name: Secret name
        value: Secret value
        description: Optional description
    """
    get_secret_manager().set(name, value, description)


def delete_secret(name: str) -> bool:
    """Convenience function to delete a secret.

    Args:
        name: Secret name

    Returns:
        True if deleted
    """
    return get_secret_manager().delete(name)


def list_secrets() -> list[SecretInfo]:
    """Convenience function to list all secrets.

    Returns:
        List of SecretInfo objects
    """
    return get_secret_manager().list()
