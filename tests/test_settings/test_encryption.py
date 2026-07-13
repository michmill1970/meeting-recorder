"""Unit tests for settings encryption."""

import pytest

from src.settings.encryption import (
    decrypt_value,
    encrypt_value,
    generate_salt,
)


class TestEncryption:
    """Tests for the encryption utilities."""

    def test_roundtrip_encrypt_decrypt(self) -> None:
        """Encrypting then decrypting should return the original value."""
        plaintext = "sk-live-abc123xyz"
        passphrase = "my_secret_passphrase"
        salt = generate_salt()

        encrypted = encrypt_value(plaintext, passphrase, salt)
        decrypted = decrypt_value(encrypted, passphrase, salt)

        assert decrypted == plaintext
        assert encrypted != plaintext
        assert encrypted != ""

    def test_different_salts_produce_different_ciphertext(self) -> None:
        """Same value + passphrase but different salt → different encrypted output."""
        plaintext = "api_key_123"
        passphrase = "passphrase"

        enc1 = encrypt_value(plaintext, passphrase, generate_salt())
        enc2 = encrypt_value(plaintext, passphrase, generate_salt())

        assert enc1 != enc2

    def test_wrong_passphrase_fails_gracefully(self) -> None:
        """Decrypting with the wrong passphrase returns None."""
        plaintext = "secret_key"
        passphrase = "correct_pass"
        wrong_passphrase = "wrong_pass"
        salt = generate_salt()

        encrypted = encrypt_value(plaintext, passphrase, salt)
        result = decrypt_value(encrypted, wrong_passphrase, salt)

        assert result is None

    def test_empty_value_encrypted(self) -> None:
        """Empty string can be encrypted and decrypted."""
        plaintext = ""
        passphrase = "pass"
        salt = generate_salt()

        encrypted = encrypt_value(plaintext, passphrase, salt)
        decrypted = decrypt_value(encrypted, passphrase, salt)

        assert decrypted == ""

    def test_salt_is_random(self) -> None:
        """Multiple calls to generate_salt produce different values."""
        salts = [generate_salt() for _ in range(10)]
        assert len(set(salts)) == 10  # All unique

    def test_salt_length(self) -> None:
        """Salt should be at least 16 bytes for security."""
        salt = generate_salt()
        assert len(salt) >= 16

    def test_long_value(self) -> None:
        """Long strings should survive encrypt/decrypt."""
        plaintext = "a" * 10_000
        passphrase = "pass"
        salt = generate_salt()

        encrypted = encrypt_value(plaintext, passphrase, salt)
        decrypted = decrypt_value(encrypted, passphrase, salt)

        assert decrypted == plaintext

    def test_special_characters(self) -> None:
        """Values with special characters should survive encrypt/decrypt."""
        plaintext = "p@ss!w0rd#$%^&*()_+-=[]{}|;':\",./<>?"
        passphrase = "pass"
        salt = generate_salt()

        encrypted = encrypt_value(plaintext, passphrase, salt)
        decrypted = decrypt_value(encrypted, passphrase, salt)

        assert decrypted == plaintext
