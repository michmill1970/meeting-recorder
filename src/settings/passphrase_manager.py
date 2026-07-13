"""Passphrase manager for encrypting sensitive settings.

Uses the OS keychain (via keyring) when available, falling back to
in-memory storage with an interactive prompt and local file backup.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
import sys
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Local passphrase backup (used when keychain is unavailable)
#
# The backup is encrypted with a machine-specific key stored alongside it.
# This prevents casual reading and ties the backup to this machine.
# ---------------------------------------------------------------------------

_SETTINGS_DIR = Path.home() / ".config" / "meeting-recorder"
_BACKUP_KEY_FILE = _SETTINGS_DIR / ".encryption_backup_key"
_PASSPHRASE_FILE = _SETTINGS_DIR / ".encryption_passphrase"

# Keychain service name used to store the encryption passphrase
_KEYCHAIN_SERVICE = "meeting-recorder"
_KEYCHAIN_USERNAME = "encryption-passphrase"


class PassphraseManager:
    """Manages the encryption passphrase using OS keychain when available."""

    def __init__(self) -> None:
        self._keyring_available = False
        self._passphrase: Optional[str] = None

        # Try to import and test keyring backend
        try:
            import keyring  # noqa: F401

            # Verify the backend actually works by doing a test write+read
            self._keyring_available = self._test_keyring_backend()
        except ImportError:
            logger.info("keyring not installed; passphrase stored in memory only")
            logger.info(
                "Install with: pip install meeting-recorder[keyring]"
            )

    @staticmethod
    def _test_keyring_backend() -> bool:
        """Test whether keyring backend is functional.

        Performs a round-trip test: write a dummy value and read it back.
        Returns True only if the round-trip succeeds.
        """
        try:
            import keyring

            test_key = "_keyring_test_" + os.urandom(8).hex()
            test_val = "test"
            keyring.set_password(_KEYCHAIN_SERVICE, test_key, test_val)
            result = keyring.get_password(_KEYCHAIN_SERVICE, test_key)
            # Clean up
            try:
                keyring.delete_password(_KEYCHAIN_SERVICE, test_key)
            except Exception:
                pass
            return result == test_val
        except Exception as e:
            logger.info("keyring backend test failed: %s", e)
            return False

    @property
    def keyring_available(self) -> bool:
        """Whether the OS keychain is available."""
        return self._keyring_available

    # ------------------------------------------------------------------
    # Passphrase backup: local file encrypted with a machine-specific key
    # ------------------------------------------------------------------

    @staticmethod
    def _get_or_create_backup_key() -> bytes:
        """Get the backup encryption key, creating it if it doesn't exist."""
        if _BACKUP_KEY_FILE.exists():
            return _BACKUP_KEY_FILE.read_bytes()
        _SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
        # Fernet requires a 32-byte url-safe base64-encoded key
        key = Fernet.generate_key()
        _BACKUP_KEY_FILE.write_bytes(key)
        # Restrict permissions: only the file owner can read/write
        os.chmod(_BACKUP_KEY_FILE, 0o600)
        logger.info("Generated new passphrase backup encryption key")
        return key

    def _save_passphrase_backup(self, passphrase: str) -> None:
        """Save the passphrase to a local file, encrypted with the backup key."""
        try:
            _SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
            key = self._get_or_create_backup_key()
            fernet = Fernet(key)
            encrypted = fernet.encrypt(passphrase.encode("utf-8")).decode("utf-8")
            _PASSPHRASE_FILE.write_text(encrypted, encoding="utf-8")
            os.chmod(_PASSPHRASE_FILE, 0o600)
            logger.info("Passphrase backed up to local file")
        except Exception as e:
            logger.warning("Failed to save passphrase backup: %s", e)

    def _load_passphrase_backup(self) -> Optional[str]:
        """Load and decrypt the passphrase from the local backup file."""
        try:
            if not _PASSPHRASE_FILE.exists():
                return None
            key = self._get_or_create_backup_key()
            fernet = Fernet(key)
            encrypted = _PASSPHRASE_FILE.read_text(encoding="utf-8").strip()
            return fernet.decrypt(encrypted.encode("utf-8")).decode("utf-8")
        except Exception as e:
            logger.warning("Failed to load passphrase backup: %s", e)
            return None

    # ------------------------------------------------------------------
    # Core passphrase methods
    # ------------------------------------------------------------------

    def get_passphrase(self) -> Optional[str]:
        """Retrieve the stored passphrase.

        Returns:
            The passphrase if found (from in-memory cache, keychain, or
            local backup), or None if not set.
        """
        # Return cached passphrase first
        if self._passphrase is not None:
            return self._passphrase

        # Try keychain
        if self._keyring_available:
            try:
                import keyring

                passphrase = keyring.get_password(
                    _KEYCHAIN_SERVICE, _KEYCHAIN_USERNAME
                )
                if passphrase:
                    self._passphrase = passphrase
                    logger.info("Passphrase loaded from keychain")
                    return passphrase
            except Exception as e:
                logger.warning("Failed to read from keychain: %s", e)
                self._keyring_available = False

        # Fallback to local backup (encrypted with machine-specific key)
        backup = self._load_passphrase_backup()
        if backup:
            self._passphrase = backup
            logger.info("Passphrase loaded from local backup")
            return backup

        return None

    def set_passphrase(self, passphrase: str) -> None:
        """Store the passphrase.

        Stores it in the OS keychain (if available and working), and always
        creates a local encrypted backup so the passphrase survives app restarts
        even when the keychain backend is unavailable.

        Args:
            passphrase: The encryption passphrase to store.
        """
        self._passphrase = passphrase

        if self._keyring_available:
            try:
                import keyring

                keyring.set_password(
                    _KEYCHAIN_SERVICE, _KEYCHAIN_USERNAME, passphrase
                )
                logger.info("Passphrase saved to keychain")
            except Exception as e:
                logger.warning("Failed to save to keychain: %s", e)

        # Always create local backup (overwrites any existing one)
        self._save_passphrase_backup(passphrase)

    def clear_passphrase(self) -> None:
        """Clear the passphrase from memory, keychain, and local backup."""
        self._passphrase = None

        if self._keyring_available:
            try:
                import keyring

                keyring.delete_password(
                    _KEYCHAIN_SERVICE, _KEYCHAIN_USERNAME
                )
                logger.info("Passphrase cleared from keychain")
            except Exception as e:
                logger.warning("Failed to clear from keychain: %s", e)

        # Remove local backup
        try:
            if _PASSPHRASE_FILE.exists():
                _PASSPHRASE_FILE.unlink()
                logger.info("Passphrase local backup removed")
        except Exception as e:
            logger.warning("Failed to remove passphrase backup: %s", e)

    def prompt_passphrase(self, title: str = "Encryption Passphrase") -> Optional[str]:
        """Prompt the user for a passphrase (fallback when keychain unavailable).

        Attempts a GUI dialog first (via PySide6), then falls back to a
        terminal prompt only when stdin/stdout are connected (i.e. running
        from a real TTY, not an app bundle).

        Args:
            title: Window/dialog title.

        Returns:
            The entered passphrase, or None if cancelled.
        """
        # --- Try GUI prompt via QInputDialog ---
        try:
            from PySide6.QtWidgets import QInputDialog, QLineEdit

            # Determine the correct EchoMode enum.  Different PySide6 builds
            # expose it differently; try all known locations.
            echo_mode = getattr(
                QLineEdit, "EchoMode", None
            )  # type: ignore[attr-defined]
            if echo_mode is not None:
                echo_mode = echo_mode.Password  # type: ignore[attr-defined]
            else:
                echo_mode = QLineEdit.Password  # type: ignore[attr-defined]

            passphrase, ok = QInputDialog.getText(
                None,
                title,
                "Enter encryption passphrase:\n"
                "(Used to encrypt API keys and tokens in settings)",
                echo=echo_mode,
            )
            if ok and passphrase:
                return passphrase
            return None
        except (ImportError, AttributeError) as exc:
            logger.debug("GUI passphrase prompt unavailable: %s", exc)

        # --- Fallback to CLI prompt ONLY when a real TTY is available ---
        if sys.stdout.isatty() and sys.stdin.isatty():
            try:
                passphrase = input("Enter encryption passphrase: ")
                return passphrase if passphrase else None
            except (EOFError, KeyboardInterrupt):
                return None

        logger.error(
            "Cannot prompt for passphrase: no GUI dialog available and "
            "not running in an interactive terminal. "
            "This is expected when running from a macOS app bundle "
            "with an empty keychain. Please ensure the system keychain "
            "is accessible or set the passphrase in Settings."
        )
        return None

    def prompt_change_passphrase(self) -> Optional[str]:
        """Prompt the user to set or change the passphrase.

        Attempts a GUI dialog first (via PySide6), then falls back to a
        terminal prompt only when stdin/stdout are connected (i.e. running
        from a real TTY, not an app bundle).

        Returns:
            The new passphrase, or None if cancelled.
        """
        # --- Try GUI prompt via QInputDialog ---
        try:
            from PySide6.QtWidgets import QInputDialog, QLineEdit

            current = self.get_passphrase()
            placeholder = (
                "Enter new passphrase (leave blank to remove)"
                if current
                else "Enter passphrase"
            )

            # Determine the correct EchoMode enum.  Different PySide6 builds
            # expose it differently; try all known locations.
            echo_mode = getattr(
                QLineEdit, "EchoMode", None
            )  # type: ignore[attr-defined]
            if echo_mode is not None:
                echo_mode = echo_mode.Password  # type: ignore[attr-defined]
            else:
                echo_mode = QLineEdit.Password  # type: ignore[attr-defined]

            passphrase, ok = QInputDialog.getText(
                None,
                "Change Encryption Passphrase",
                f"{placeholder}:\n"
                f"{'(Currently set)' if current else '(Not set)'}",
                echo=echo_mode,
                text=current if current else "",
            )
            if ok:
                if passphrase:
                    return passphrase
                # Empty string means user wants to remove passphrase
                return ""
            return None
        except (ImportError, AttributeError) as exc:
            logger.debug("GUI passphrase prompt unavailable: %s", exc)

        # --- Fallback to CLI prompt ONLY when a real TTY is available ---
        if sys.stdout.isatty() and sys.stdin.isatty():
            try:
                current = self.get_passphrase()
                prompt = (
                    "Enter new passphrase (leave blank to remove):"
                    if current
                    else "Enter passphrase:"
                )
                passphrase = input(prompt)
                return passphrase if passphrase else ""
            except (EOFError, KeyboardInterrupt):
                return None

        logger.error(
            "Cannot prompt for passphrase: no GUI dialog available and "
            "not running in an interactive terminal."
        )
        return None
