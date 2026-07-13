"""Unit tests for passphrase manager."""

import pytest

from src.settings.passphrase_manager import PassphraseManager


class TestPassphraseManager:
    """Tests for PassphraseManager."""

    def test_initialization(self) -> None:
        """Manager should initialize without error."""
        pm = PassphraseManager()
        assert pm.get_passphrase() is None

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
