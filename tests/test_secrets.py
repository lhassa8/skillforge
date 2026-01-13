"""Tests for secrets management."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from skillforge.secrets import (
    # Encryption
    encrypt_value,
    decrypt_value,
    _simple_encrypt,
    _simple_decrypt,
    _get_or_create_key,
    EncryptionError,
    # Backends
    SecretBackend,
    EnvSecretBackend,
    FileSecretBackend,
    VaultSecretBackend,
    SecretInfo,
    SecretNotFoundError,
    SecretBackendError,
    # Manager
    SecretManager,
    # Placeholder resolution
    SECRET_PLACEHOLDER_PATTERN,
    extract_secret_placeholders,
    resolve_secrets,
    resolve_secrets_in_dict,
    # Masking
    SecretMasker,
    MASK_CHAR,
    MASK_LENGTH,
    # Globals
    get_secret_manager,
    get_secret_masker,
    reset_globals,
    # Utilities
    init_secrets_dir,
    mask_in_command,
    get_secret,
    set_secret,
    delete_secret,
    list_secrets,
)


class TestEncryption:
    """Tests for encryption utilities."""

    def test_simple_encrypt_decrypt_roundtrip(self):
        """Test simple encryption/decryption roundtrip."""
        key = os.urandom(32)
        plaintext = "Hello, World! This is a test."

        encrypted = _simple_encrypt(plaintext.encode(), key)
        decrypted = _simple_decrypt(encrypted, key)

        assert decrypted.decode() == plaintext

    def test_simple_encrypt_produces_different_ciphertext(self):
        """Test that encryption produces different ciphertext each time (due to IV)."""
        key = os.urandom(32)
        plaintext = b"test data"

        encrypted1 = _simple_encrypt(plaintext, key)
        encrypted2 = _simple_encrypt(plaintext, key)

        # Should be different due to random IV
        assert encrypted1 != encrypted2

    def test_simple_decrypt_invalid_data(self):
        """Test decryption with invalid data."""
        key = os.urandom(32)

        with pytest.raises(EncryptionError):
            _simple_decrypt(b"too short", key)

    def test_encrypt_value_with_prefix(self):
        """Test that encrypted values have the correct prefix."""
        key = os.urandom(32)
        encrypted = encrypt_value("secret", key)

        # Should have either "simple:" or "fernet:" prefix
        assert encrypted.startswith("simple:") or encrypted.startswith("fernet:")

    def test_encrypt_decrypt_value_roundtrip(self):
        """Test encrypt/decrypt value roundtrip."""
        key = os.urandom(32)
        plaintext = "my_secret_value"

        encrypted = encrypt_value(plaintext, key)
        decrypted = decrypt_value(encrypted, key)

        assert decrypted == plaintext

    def test_decrypt_legacy_plain_value(self):
        """Test decrypting a plain (unencrypted) value."""
        key = os.urandom(32)

        # Plain values without prefix are returned as-is
        result = decrypt_value("plain_text", key)
        assert result == "plain_text"


class TestEnvSecretBackend:
    """Tests for environment variable secret backend."""

    def test_get_secret_from_env(self):
        """Test retrieving a secret from environment."""
        backend = EnvSecretBackend(prefix="TEST_SECRET_")

        with patch.dict(os.environ, {"TEST_SECRET_API_KEY": "my-api-key"}):
            value = backend.get("api_key")
            assert value == "my-api-key"

    def test_get_nonexistent_secret(self):
        """Test getting a non-existent secret raises error."""
        backend = EnvSecretBackend(prefix="TEST_SECRET_")

        with pytest.raises(SecretNotFoundError):
            backend.get("nonexistent")

    def test_set_raises_error(self):
        """Test that set raises error (read-only backend)."""
        backend = EnvSecretBackend()

        with pytest.raises(SecretBackendError, match="read-only"):
            backend.set("name", "value")

    def test_delete_raises_error(self):
        """Test that delete raises error (read-only backend)."""
        backend = EnvSecretBackend()

        with pytest.raises(SecretBackendError, match="read-only"):
            backend.delete("name")

    def test_list_secrets(self):
        """Test listing secrets from environment."""
        backend = EnvSecretBackend(prefix="TEST_LIST_")

        with patch.dict(os.environ, {
            "TEST_LIST_SECRET1": "value1",
            "TEST_LIST_SECRET2": "value2",
            "OTHER_VAR": "other",
        }):
            secrets = backend.list()
            names = [s.name for s in secrets]

            assert "secret1" in names
            assert "secret2" in names
            assert len(secrets) == 2

    def test_exists(self):
        """Test checking if secret exists."""
        backend = EnvSecretBackend(prefix="TEST_EXISTS_")

        with patch.dict(os.environ, {"TEST_EXISTS_KEY": "value"}):
            assert backend.exists("key")
            assert not backend.exists("nonexistent")

    def test_name_property(self):
        """Test backend name."""
        backend = EnvSecretBackend()
        assert backend.name == "env"


class TestFileSecretBackend:
    """Tests for encrypted file secret backend."""

    def test_set_and_get_secret(self):
        """Test setting and getting a secret."""
        with tempfile.TemporaryDirectory() as tmp:
            secrets_file = Path(tmp) / "secrets.enc"
            metadata_file = Path(tmp) / "metadata.yaml"

            backend = FileSecretBackend(
                secrets_file=secrets_file,
                metadata_file=metadata_file,
            )

            backend.set("my_secret", "secret_value", "Test secret")

            assert backend.get("my_secret") == "secret_value"

    def test_get_nonexistent_secret(self):
        """Test getting a non-existent secret."""
        with tempfile.TemporaryDirectory() as tmp:
            secrets_file = Path(tmp) / "secrets.enc"
            metadata_file = Path(tmp) / "metadata.yaml"

            backend = FileSecretBackend(
                secrets_file=secrets_file,
                metadata_file=metadata_file,
            )

            with pytest.raises(SecretNotFoundError):
                backend.get("nonexistent")

    def test_delete_secret(self):
        """Test deleting a secret."""
        with tempfile.TemporaryDirectory() as tmp:
            secrets_file = Path(tmp) / "secrets.enc"
            metadata_file = Path(tmp) / "metadata.yaml"

            backend = FileSecretBackend(
                secrets_file=secrets_file,
                metadata_file=metadata_file,
            )

            backend.set("to_delete", "value")
            assert backend.exists("to_delete")

            result = backend.delete("to_delete")
            assert result is True
            assert not backend.exists("to_delete")

    def test_delete_nonexistent(self):
        """Test deleting non-existent secret returns False."""
        with tempfile.TemporaryDirectory() as tmp:
            secrets_file = Path(tmp) / "secrets.enc"
            metadata_file = Path(tmp) / "metadata.yaml"

            backend = FileSecretBackend(
                secrets_file=secrets_file,
                metadata_file=metadata_file,
            )

            assert backend.delete("nonexistent") is False

    def test_list_secrets(self):
        """Test listing secrets."""
        with tempfile.TemporaryDirectory() as tmp:
            secrets_file = Path(tmp) / "secrets.enc"
            metadata_file = Path(tmp) / "metadata.yaml"

            backend = FileSecretBackend(
                secrets_file=secrets_file,
                metadata_file=metadata_file,
            )

            backend.set("secret1", "value1")
            backend.set("secret2", "value2", "Description")

            secrets = backend.list()
            names = [s.name for s in secrets]

            assert "secret1" in names
            assert "secret2" in names
            assert len(secrets) == 2

    def test_persistence(self):
        """Test that secrets persist across instances."""
        with tempfile.TemporaryDirectory() as tmp:
            secrets_file = Path(tmp) / "secrets.enc"
            metadata_file = Path(tmp) / "metadata.yaml"

            # Set secret in first instance
            backend1 = FileSecretBackend(
                secrets_file=secrets_file,
                metadata_file=metadata_file,
            )
            backend1.set("persistent", "my_value")

            # Load in second instance
            backend2 = FileSecretBackend(
                secrets_file=secrets_file,
                metadata_file=metadata_file,
            )

            assert backend2.get("persistent") == "my_value"

    def test_name_property(self):
        """Test backend name."""
        with tempfile.TemporaryDirectory() as tmp:
            backend = FileSecretBackend(
                secrets_file=Path(tmp) / "s.enc",
                metadata_file=Path(tmp) / "m.yaml",
            )
            assert backend.name == "file"


class TestSecretManager:
    """Tests for SecretManager."""

    def test_get_from_env_backend(self):
        """Test getting secret from env backend."""
        env_backend = EnvSecretBackend(prefix="TEST_MGR_")
        manager = SecretManager(backends=[env_backend])

        with patch.dict(os.environ, {"TEST_MGR_TOKEN": "my-token"}):
            value = manager.get("token")
            assert value == "my-token"

    def test_get_falls_through_backends(self):
        """Test that get tries backends in order."""
        with tempfile.TemporaryDirectory() as tmp:
            env_backend = EnvSecretBackend(prefix="TEST_FALLBACK_")
            file_backend = FileSecretBackend(
                secrets_file=Path(tmp) / "s.enc",
                metadata_file=Path(tmp) / "m.yaml",
            )

            manager = SecretManager(backends=[env_backend, file_backend])

            # Set in file backend
            file_backend.set("file_only", "from_file")

            # Should find it via fallback
            assert manager.get("file_only") == "from_file"

    def test_get_not_found(self):
        """Test getting non-existent secret."""
        manager = SecretManager(backends=[])

        with pytest.raises(SecretNotFoundError):
            manager.get("nonexistent")

    def test_set_to_specific_backend(self):
        """Test setting secret to specific backend."""
        with tempfile.TemporaryDirectory() as tmp:
            file_backend = FileSecretBackend(
                secrets_file=Path(tmp) / "s.enc",
                metadata_file=Path(tmp) / "m.yaml",
            )

            manager = SecretManager(backends=[file_backend])
            manager.set("new_secret", "value", backend_name="file")

            assert manager.get("new_secret") == "value"

    def test_set_backend_not_found(self):
        """Test setting to non-existent backend."""
        manager = SecretManager(backends=[])

        with pytest.raises(SecretBackendError, match="Backend not found"):
            manager.set("name", "value", backend_name="nonexistent")

    def test_delete(self):
        """Test deleting a secret."""
        with tempfile.TemporaryDirectory() as tmp:
            file_backend = FileSecretBackend(
                secrets_file=Path(tmp) / "s.enc",
                metadata_file=Path(tmp) / "m.yaml",
            )

            manager = SecretManager(backends=[file_backend])
            manager.set("to_delete", "value")

            assert manager.delete("to_delete")
            assert not manager.exists("to_delete")

    def test_list_all_backends(self):
        """Test listing secrets from all backends."""
        with tempfile.TemporaryDirectory() as tmp:
            env_backend = EnvSecretBackend(prefix="TEST_LISTALL_")
            file_backend = FileSecretBackend(
                secrets_file=Path(tmp) / "s.enc",
                metadata_file=Path(tmp) / "m.yaml",
            )

            manager = SecretManager(backends=[env_backend, file_backend])
            file_backend.set("file_secret", "value")

            with patch.dict(os.environ, {"TEST_LISTALL_ENV_SECRET": "value"}):
                secrets = manager.list()
                names = [s.name for s in secrets]

                assert "file_secret" in names
                assert "env_secret" in names

    def test_exists(self):
        """Test checking if secret exists."""
        with tempfile.TemporaryDirectory() as tmp:
            file_backend = FileSecretBackend(
                secrets_file=Path(tmp) / "s.enc",
                metadata_file=Path(tmp) / "m.yaml",
            )

            manager = SecretManager(backends=[file_backend])
            file_backend.set("exists", "value")

            assert manager.exists("exists")
            assert not manager.exists("nonexistent")

    def test_get_backend_names(self):
        """Test getting backend names."""
        env_backend = EnvSecretBackend()
        manager = SecretManager(backends=[env_backend])

        names = manager.get_backend_names()
        assert "env" in names


class TestPlaceholderResolution:
    """Tests for secret placeholder resolution."""

    def test_extract_secret_placeholders(self):
        """Test extracting secret placeholders."""
        text = "API key: {secret:api_key}, DB: {secret:database_url}"

        placeholders = extract_secret_placeholders(text)

        assert "api_key" in placeholders
        assert "database_url" in placeholders

    def test_extract_no_placeholders(self):
        """Test extracting from text without placeholders."""
        text = "No secrets here, just {regular_placeholder}"

        placeholders = extract_secret_placeholders(text)

        assert placeholders == []

    def test_resolve_secrets(self):
        """Test resolving secret placeholders."""
        with tempfile.TemporaryDirectory() as tmp:
            file_backend = FileSecretBackend(
                secrets_file=Path(tmp) / "s.enc",
                metadata_file=Path(tmp) / "m.yaml",
            )
            file_backend.set("token", "secret123")

            manager = SecretManager(backends=[file_backend])

            text = "Token: {secret:token}"
            result = resolve_secrets(text, manager)

            assert result == "Token: secret123"

    def test_resolve_secrets_not_found(self):
        """Test resolving non-existent secret."""
        manager = SecretManager(backends=[])

        text = "Token: {secret:nonexistent}"

        with pytest.raises(SecretNotFoundError):
            resolve_secrets(text, manager)

    def test_resolve_secrets_in_dict(self):
        """Test resolving secrets in nested dictionary."""
        with tempfile.TemporaryDirectory() as tmp:
            file_backend = FileSecretBackend(
                secrets_file=Path(tmp) / "s.enc",
                metadata_file=Path(tmp) / "m.yaml",
            )
            file_backend.set("api_key", "key123")

            manager = SecretManager(backends=[file_backend])

            data = {
                "config": {
                    "api_key": "{secret:api_key}",
                    "nested": {
                        "key": "{secret:api_key}",
                    },
                },
                "list": ["{secret:api_key}"],
            }

            result = resolve_secrets_in_dict(data, manager)

            assert result["config"]["api_key"] == "key123"
            assert result["config"]["nested"]["key"] == "key123"
            assert result["list"][0] == "key123"


class TestSecretMasker:
    """Tests for SecretMasker."""

    def test_mask_secret_in_text(self):
        """Test masking a secret in text."""
        masker = SecretMasker()
        masker.add_secret("password123")

        text = "The password is password123 and it's secret."
        masked = masker.mask(text)

        assert "password123" not in masked
        assert MASK_CHAR * MASK_LENGTH in masked

    def test_mask_multiple_occurrences(self):
        """Test masking multiple occurrences."""
        masker = SecretMasker()
        masker.add_secret("secret")

        text = "secret appears secret twice"
        masked = masker.mask(text)

        assert masked.count(MASK_CHAR * MASK_LENGTH) == 2

    def test_mask_short_values_ignored(self):
        """Test that very short values are not masked."""
        masker = SecretMasker()
        masker.add_secret("ab")  # Too short

        text = "ab is here"
        masked = masker.mask(text)

        assert masked == text  # Not masked

    def test_add_multiple_secrets(self):
        """Test adding multiple secrets."""
        masker = SecretMasker()
        masker.add_secrets(["secret1", "secret2"])

        text = "secret1 and secret2"
        masked = masker.mask(text)

        assert "secret1" not in masked
        assert "secret2" not in masked

    def test_mask_dict(self):
        """Test masking secrets in a dictionary."""
        masker = SecretMasker()
        masker.add_secret("password")

        data = {
            "message": "password is here",
            "nested": {"key": "password"},
            "list": ["password"],
        }

        masked = masker.mask_dict(data)

        assert "password" not in masked["message"]
        assert "password" not in masked["nested"]["key"]
        assert "password" not in masked["list"][0]

    def test_clear(self):
        """Test clearing all secrets."""
        masker = SecretMasker()
        masker.add_secret("secret")
        masker.clear()

        text = "secret is visible"
        masked = masker.mask(text)

        assert masked == text  # Not masked

    def test_add_from_manager(self):
        """Test adding secrets from manager."""
        with tempfile.TemporaryDirectory() as tmp:
            file_backend = FileSecretBackend(
                secrets_file=Path(tmp) / "s.enc",
                metadata_file=Path(tmp) / "m.yaml",
            )
            file_backend.set("db_password", "secret_password")

            manager = SecretManager(backends=[file_backend])

            masker = SecretMasker()
            masker.add_from_manager(manager)

            text = "DB password: secret_password"
            masked = masker.mask(text)

            assert "secret_password" not in masked


class TestGlobals:
    """Tests for global manager and masker."""

    def test_reset_globals(self):
        """Test resetting globals."""
        # Access globals to create them
        manager1 = get_secret_manager()

        # Reset
        reset_globals()

        # Should get new instance
        manager2 = get_secret_manager()

        # This works because we're testing the reset mechanism
        # The instances should be functionally equivalent but different objects
        assert manager2 is not manager1


class TestUtilities:
    """Tests for utility functions."""

    def test_mask_in_command(self):
        """Test masking secrets in command string."""
        with tempfile.TemporaryDirectory() as tmp:
            file_backend = FileSecretBackend(
                secrets_file=Path(tmp) / "s.enc",
                metadata_file=Path(tmp) / "m.yaml",
            )
            file_backend.set("api_key", "super_secret_key")

            manager = SecretManager(backends=[file_backend])

            command = "curl -H 'Authorization: super_secret_key' https://api.example.com"
            masked = mask_in_command(command, manager)

            assert "super_secret_key" not in masked


class TestPlaceholdersIntegration:
    """Tests for placeholder integration with secrets."""

    def test_substitute_with_secrets(self):
        """Test placeholder substitution with secrets."""
        from skillforge.placeholders import substitute

        with tempfile.TemporaryDirectory() as tmp:
            file_backend = FileSecretBackend(
                secrets_file=Path(tmp) / "s.enc",
                metadata_file=Path(tmp) / "m.yaml",
            )
            file_backend.set("token", "my_token_value")

            manager = SecretManager(backends=[file_backend])

            template = "API Token: {secret:token}, Target: {target_dir}"
            context = {"target_dir": "/path/to/target"}

            result = substitute(template, context, manager)

            assert result == "API Token: my_token_value, Target: /path/to/target"

    def test_substitute_dict_with_secrets(self):
        """Test dict substitution with secrets."""
        from skillforge.placeholders import substitute_dict

        with tempfile.TemporaryDirectory() as tmp:
            file_backend = FileSecretBackend(
                secrets_file=Path(tmp) / "s.enc",
                metadata_file=Path(tmp) / "m.yaml",
            )
            file_backend.set("db_pass", "secret_pass")

            manager = SecretManager(backends=[file_backend])

            data = {
                "env": {"DATABASE_PASSWORD": "{secret:db_pass}"},
                "command": "echo {target_dir}",
            }
            context = {"target_dir": "/app"}

            result = substitute_dict(data, context, manager)

            assert result["env"]["DATABASE_PASSWORD"] == "secret_pass"
            assert result["command"] == "echo /app"

    def test_extract_secret_placeholders_from_placeholders_module(self):
        """Test extract_secret_placeholders from placeholders module."""
        from skillforge.placeholders import (
            extract_secret_placeholders as extract,
            has_secret_placeholders,
        )

        template = "Key: {secret:api_key}"

        assert has_secret_placeholders(template)
        assert "api_key" in extract(template)

        plain = "No secrets: {regular}"

        assert not has_secret_placeholders(plain)
        assert extract(plain) == []
