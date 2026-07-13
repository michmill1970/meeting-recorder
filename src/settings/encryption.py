"""Encryption utilities for sensitive settings fields.

Provides Fernet-based encryption for API keys and tokens,
keyed by a user-provided passphrase.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


def derive_key(passphrase: str, salt: bytes) -> bytes:
    """Derive a 32-byte Fernet key from a passphrase using PBKDF2-HMAC-SHA256.

    Args:
        passphrase: User-provided passphrase.
        salt: Random salt bytes (at least 16 bytes recommended).

    Returns:
        A base64-encoded 32-byte key suitable for Fernet.
    """
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        passphrase.encode("utf-8"),
        salt,
        iterations=100_000,
    )
    return base64.urlsafe_b64encode(dk[:32])


def encrypt_value(value: str, passphrase: str, salt: bytes) -> str:
    """Encrypt a string value with Fernet.

    Args:
        value: Plaintext value to encrypt.
        passphrase: User passphrase for key derivation.
        salt: Salt for key derivation.

    Returns:
        Base64-encoded Fernet token.
    """
    key = derive_key(passphrase, salt)
    fernet = Fernet(key)
    return fernet.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_value(encrypted: str, passphrase: str, salt: bytes) -> Optional[str]:
    """Decrypt a Fernet-encrypted value.

    Args:
        encrypted: Base64-encoded Fernet token.
        passphrase: User passphrase for key derivation.
        salt: Salt for key derivation.

    Returns:
        Decrypted plaintext, or None if decryption fails.
    """
    try:
        key = derive_key(passphrase, salt)
        fernet = Fernet(key)
        return fernet.decrypt(encrypted.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        logger.warning("Failed to decrypt sensitive setting (wrong passphrase)")
        return None
    except Exception as e:
        logger.warning("Error decrypting sensitive setting: %s", e)
        return None


def generate_salt() -> bytes:
    """Generate a random salt for key derivation."""
    return os.urandom(16)
