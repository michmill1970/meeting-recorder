"""Unit tests for passphrase manager."""

import tempfile
from pathlib import Path

import pytest

from src.settings.passphrase_manager import PassphraseManager


class TestPassphraseManager:
    """Tests for PassphraseManager."""

    def test_initialization(self, tmp_dir: Path) -> None:
        """Manager should initialize without error."""
        from src.settings import passphrase_manager as pm_module

        original_dir = pm_module._SETTINGS_DIR
        pm_module._SETTINGS_DIR = tmp_dir
        pm_module._BACKUP_KEY_FILE = tmp_dir / ".encryption_backup_key"
        pm_module._PASSPHRASE_FILE = tmp_dir / ".encryption_passphrase"

        try:
            pm = PassphraseManager()
            assert pm.get_passphrase() is None
        finally:
            pm_module._SETTINGS_DIR = original_dir
            pm_module._BACKUP_KEY_FILE = original_dir / ".encryption_backup_key"
            pm_module._PASSPHRASE_FILE = original_dir / ".encryption_passphrase"

    def test_set_and_get_passphrase(self) -> None:
        """Setting and getting a passphrase should work."""
        pm = PassphraseManager()
        pm.set_passphrase("test_passphrase")
        assert pm.get_passphrase() == "test_passphrase"

    def test_get_passphrase_returns_cached(self) -> None:
        """Subsequent calls should return the cached passphrase."""
        pm = PassphraseManager()
        pm.set_passphrase("my_pass")
        assert pm.get_passphrase() == "my_pass"
        assert pm.get_passphrase() == "my_pass"  # Should return cached value

    def test_clear_passphrase(self) -> None:
        """Clearing passphrase should return None."""
        pm = PassphraseManager()
        pm.set_passphrase("my_pass")
        pm.clear_passphrase()
        assert pm.get_passphrase() is None

    def test_keyring_available_flag(self) -> None:
        """keyring_available should reflect whether keyring is installed."""
        pm = PassphraseManager()
        # At minimum, it should be a boolean
        assert isinstance(pm.keyring_available, bool)

    def test_empty_passphrase_not_set(self) -> None:
        """Setting an empty passphrase should still work (for removal)."""
        pm = PassphraseManager()
        pm.set_passphrase("")
        # Empty string is a valid passphrase (used for removal)
        assert pm.get_passphrase() == ""

    def test_passphrase_backup_survives_new_instance(self, tmp_dir: Path) -> None:
        """Passphrase saved via set_passphrase should survive a new manager instance."""
        from src.settings import passphrase_manager as pm_module

        # Temporarily redirect settings directory
        original_dir = pm_module._SETTINGS_DIR
        pm_module._SETTINGS_DIR = tmp_dir
        pm_module._BACKUP_KEY_FILE = tmp_dir / ".encryption_backup_key"
        pm_module._PASSPHRASE_FILE = tmp_dir / ".encryption_passphrase"

        try:
            pm1 = PassphraseManager()
            pm1.set_passphrase("backup_test_pass")

            # New instance should recover the passphrase from backup
            pm2 = PassphraseManager()
            assert pm2.get_passphrase() == "backup_test_pass"
        finally:
            pm_module._SETTINGS_DIR = original_dir
            pm_module._BACKUP_KEY_FILE = original_dir / ".encryption_backup_key"
            pm_module._PASSPHRASE_FILE = original_dir / ".encryption_passphrase"

    def test_clear_passphrase_removes_backup(self, tmp_dir: Path) -> None:
        """Clearing passphrase should remove the local backup file."""
        from src.settings import passphrase_manager as pm_module

        original_dir = pm_module._SETTINGS_DIR
        pm_module._SETTINGS_DIR = tmp_dir
        pm_module._BACKUP_KEY_FILE = tmp_dir / ".encryption_backup_key"
        pm_module._PASSPHRASE_FILE = tmp_dir / ".encryption_passphrase"

        try:
            pm = PassphraseManager()
            pm.set_passphrase("clear_test")
            assert (tmp_dir / ".encryption_passphrase").exists()

            pm.clear_passphrase()
            assert not (tmp_dir / ".encryption_passphrase").exists()
        finally:
            pm_module._SETTINGS_DIR = original_dir
            pm_module._BACKUP_KEY_FILE = original_dir / ".encryption_backup_key"
            pm_module._PASSPHRASE_FILE = original_dir / ".encryption_passphrase"
