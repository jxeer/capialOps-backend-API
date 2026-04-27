"""
Encryption utilities for sensitive data fields.

SECURITY: AES-256-GCM provides both confidentiality and authenticity (authenticated encryption).
Unlike AES-CBC or ECB, GCM includes an authentication tag that detects tampering.

KEY GENERATION:
    python -c "import os, base64; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"

This value must be:
    1. Set in .env as FIELD_ENCRYPTION_KEY
    2. Set in Railway environment variables

WARNING: If you lose this key, encrypted data is UNRECOVERABLE.
"""

import base64
import os
from typing import Optional

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Load encryption key from environment
_field_encryption_key: Optional[bytes] = None


def _get_key() -> bytes:
    """Load and validate the encryption key from FIELD_ENCRYPTION_KEY env var."""
    global _field_encryption_key
    if _field_encryption_key is None:
        key_b64 = os.environ.get("FIELD_ENCRYPTION_KEY")
        if not key_b64:
            raise EncryptionError(
                "FIELD_ENCRYPTION_KEY environment variable is not set. "
                "Generate a key with: python -c \"import os, base64; print(base64.urlsafe_b64encode(os.urandom(32)).decode())\""
            )
        try:
            _field_encryption_key = base64.urlsafe_b64decode(key_b64)
        except Exception as e:
            raise EncryptionError(f"Invalid base64 encoding for FIELD_ENCRYPTION_KEY: {e}")
        if len(_field_encryption_key) != 32:
            raise EncryptionError(
                f"FIELD_ENCRYPTION_KEY must be 32 bytes (got {len(_field_encryption_key)}). "
                "Generate a valid key with: python -c \"import os, base64; print(base64.urlsafe_b64encode(os.urandom(32)).decode())\""
            )
    return _field_encryption_key


def _reset_key_cache():
    """Reset the cached encryption key. Used for testing."""
    global _field_encryption_key
    _field_encryption_key = None


# Prefix to identify encrypted values (base64 encoded "enc::")
_ENCRYPTION_PREFIX_BYTES = base64.urlsafe_b64encode(b"enc::")


def is_encrypted(value: str) -> bool:
    """
    Check if a value appears to be encrypted.

    Returns True if the value starts with the encryption prefix, False otherwise.
    This allows safe re-running of migrations without re-encrypting already-encrypted data.

    Args:
        value: The string to check

    Returns:
        True if value appears encrypted, False otherwise
    """
    if value is None:
        return False
    if not isinstance(value, str):
        return False
    return value.startswith("enc_")


def encrypt_value(plaintext: str) -> str:
    """
    Encrypt a plaintext string using AES-256-GCM.

    Args:
        plaintext: The string to encrypt

    Returns:
        Base64-encoded string in format: enc_<nonce><ciphertext+tag>
        The nonce (12 bytes) is prepended to the ciphertext, and the auth tag (16 bytes) is appended.

    Raises:
        EncryptionError: If encryption fails
    """
    if plaintext is None:
        return None

    try:
        key = _get_key()
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        combined = nonce + ciphertext
        return "enc_" + base64.urlsafe_b64encode(combined).decode("ascii")
    except EncryptionError:
        raise
    except Exception as e:
        raise EncryptionError(f"Encryption failed: {e}")


def decrypt_value(ciphertext: str) -> str:
    """
    Decrypt an AES-256-GCM encrypted string.

    Args:
        ciphertext: Base64-encoded string from encrypt_value()

    Returns:
        The original plaintext string

    Raises:
        EncryptionError: If decryption fails (wrong key, corrupt data, or tampered)
    """
    if ciphertext is None:
        return None

    if not is_encrypted(ciphertext):
        raise EncryptionError(
            f"Value does not have encryption prefix. Either this value is not encrypted "
            f"(stored plaintext) or was encrypted with a different method. Value: {ciphertext[:50]}..."
        )

    try:
        key = _get_key()
        encrypted_data = base64.urlsafe_b64decode(ciphertext[4:])
        nonce = encrypted_data[:12]
        actual_ciphertext = encrypted_data[12:]
        aesgcm = AESGCM(key)
        plaintext_bytes = aesgcm.decrypt(nonce, actual_ciphertext, None)
        return plaintext_bytes.decode("utf-8")
    except EncryptionError:
        raise
    except Exception as e:
        raise EncryptionError(f"Decryption failed (data may be corrupt or wrong key): {e}")


class EncryptionError(Exception):
    """Raised when encryption or decryption operations fail."""
    pass


# =============================================================================
# SQLAlchemy TypeDecorator
# =============================================================================

from sqlalchemy import TypeDecorator, Text


class EncryptedString(TypeDecorator):
    """
    A SQLAlchemy TypeDecorator that transparently encrypts/decrypts string values.

    Usage in models:
        from app.utils.encryption import EncryptedString

        class User(db.Model):
            ssn = db.Column(EncryptedString(200))

    Storage:
        - Internally uses Text (VARCHAR without length limit)
        - Encrypted values are prefixed with 'enc_' for identification
        - None values remain None (no encryption/decryption attempted)
    """
    impl = Text
    cache_ok = True

    def __init__(self, length=None):
        super().__init__()
        self.length = length

    def process_bind_param(self, value, dialect):
        """Encrypt value before storing in database."""
        if value is None:
            return None
        encrypted = encrypt_value(str(value))
        return encrypted

    def process_result_value(self, value, dialect):
        """Decrypt value when reading from database."""
        if value is None:
            return None
        if not is_encrypted(value):
            return value
        return decrypt_value(value)

    def copy(self):
        return EncryptedString(length=self.length)