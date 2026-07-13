"""Passphrase manager for encrypting sensitive settings.

Uses the OS keychain (via keyring) when available, falling back to
in-memory storage with an interactive prompt.
"""

from __future__ import annotations

import logging
import sys
from typing import Optional

logger = logging.getLogger(__name__)

# Keychain service name used to store the encryption passphrase
_KEYCHAIN_SERVICE = "meeting-recorder"
_KEYCHAIN_USERNAME = "encryption-passphrase"


class PassphraseManager:
    """Manages the encryption passphrase using OS keychain when available."""

    def __init__(self) -> None:
        self._keyring_available = False
        self._passphrase: Optional[str] = None

        # Try to import keyring
        try:
            import keyring  # noqa: F401

            self._keyring_available = True
        except ImportError:
            logger.info("keyring not installed; passphrase stored in memory only")
            logger.info(
                "Install with: pip install meeting-recorder[keyring]"
            )

    @property
    def keyring_available(self) -> bool:
        """Whether the OS keychain is available."""
        return self._keyring_available

    def get_passphrase(self) -> Optional[str]:
        """Retrieve the stored passphrase.

        Returns:
            The passphrase if found (from keychain or in-memory cache),
            or None if not set.
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

        return None

    def set_passphrase(self, passphrase: str) -> None:
        """Store the passphrase.

        If keychain is available, stores it there and caches in memory.
        Otherwise, caches in memory only (will be lost on app restart).

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
                logger.info("Passphrase cached in memory only")

    def clear_passphrase(self) -> None:
        """Clear the passphrase from memory and keychain."""
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

    def prompt_passphrase(self, title: str = "Encryption Passphrase") -> Optional[str]:
        """Prompt the user for a passphrase (fallback when keychain unavailable).

        Args:
            title: Window/dialog title.

        Returns:
            The entered passphrase, or None if cancelled.
        """
        try:
            from PySide6.QtWidgets import QInputDialog

            passphrase, ok = QInputDialog.getText(
                None,
                title,
                "Enter encryption passphrase:\n"
                "(Used to encrypt API keys and tokens in settings)",
                echo=QInputDialog.EchoMode.Password,
            )
            if ok and passphrase:
                return passphrase
            return None
        except ImportError:
            # Fallback to terminal prompt when no GUI available
            try:
                passphrase = input("Enter encryption passphrase: ")
                return passphrase if passphrase else None
            except (EOFError, KeyboardInterrupt):
                return None

    def prompt_change_passphrase(self) -> Optional[str]:
        """Prompt the user to set or change the passphrase.

        Returns:
            The new passphrase, or None if cancelled.
        """
        try:
            from PySide6.QtWidgets import QInputDialog

            current = self.get_passphrase()
            placeholder = "Enter new passphrase (leave blank to remove)" if current else "Enter passphrase"

            passphrase, ok = QInputDialog.getText(
                None,
                "Change Encryption Passphrase",
                f"{placeholder}:\n"
                f"{'(Currently set)' if current else '(Not set)'}",
                echo=QInputDialog.EchoMode.Password,
                text=current if current else "",
            )
            if ok:
                if passphrase:
                    return passphrase
                # Empty string means user wants to remove passphrase
                return ""
            return None
        except ImportError:
            try:
                current = self.get_passphrase()
                prompt = "Enter new passphrase (leave blank to remove):" if current else "Enter passphrase:"
                passphrase = input(prompt)
                return passphrase if passphrase else ""
            except (EOFError, KeyboardInterrupt):
                return None
