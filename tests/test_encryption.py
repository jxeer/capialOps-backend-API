"""
Unit tests for encryption utilities.

Run with: pytest tests/test_encryption.py -v
"""

import os
import base64
import pytest

os.environ["FIELD_ENCRYPTION_KEY"] = base64.urlsafe_b64encode(os.urandom(32)).decode()


from app.utils.encryption import (
    encrypt_value,
    decrypt_value,
    is_encrypted,
    EncryptionError,
    _reset_key_cache,
)


class TestIsEncrypted:
    def test_returns_false_for_none(self):
        assert is_encrypted(None) is False

    def test_returns_false_for_plaintext(self):
        assert is_encrypted("hello world") is False
        assert is_encrypted("123-45-6789") is False

    def test_returns_true_for_encrypted(self):
        key = base64.urlsafe_b64encode(os.urandom(32)).decode()
        os.environ["FIELD_ENCRYPTION_KEY"] = key
        encrypted = encrypt_value("secret data")
        assert is_encrypted(encrypted) is True


class TestEncryptDecrypt:
    def test_roundtrip_simple_string(self):
        plaintext = "Hello, World!"
        encrypted = encrypt_value(plaintext)
        assert is_encrypted(encrypted)
        decrypted = decrypt_value(encrypted)
        assert decrypted == plaintext

    def test_roundtrip_ssn_format(self):
        plaintext = "123-45-6789"
        encrypted = encrypt_value(plaintext)
        decrypted = decrypt_value(encrypted)
        assert decrypted == plaintext

    def test_roundtrip_empty_string(self):
        plaintext = ""
        encrypted = encrypt_value(plaintext)
        decrypted = decrypt_value(encrypted)
        assert decrypted == plaintext

    def test_roundtrip_unicode(self):
        plaintext = "日本語テスト123"
        encrypted = encrypt_value(plaintext)
        decrypted = decrypt_value(encrypted)
        assert decrypted == plaintext

    def test_roundtrip_long_text(self):
        plaintext = "A" * 10000
        encrypted = encrypt_value(plaintext)
        decrypted = decrypt_value(encrypted)
        assert decrypted == plaintext

    def test_different_encryptions_produce_different_ciphertext(self):
        plaintext = "same text"
        enc1 = encrypt_value(plaintext)
        enc2 = encrypt_value(plaintext)
        assert enc1 != enc2
        assert decrypt_value(enc1) == decrypt_value(enc2) == plaintext


class TestNonePassthrough:
    def test_encrypt_none_returns_none(self):
        assert encrypt_value(None) is None

    def test_decrypt_none_returns_none(self):
        assert decrypt_value(None) is None

    def test_is_encrypted_none_returns_false(self):
        assert is_encrypted(None) is False


class TestEncryptionError:
    def test_decrypt_non_encrypted_value_raises(self):
        with pytest.raises(EncryptionError) as exc_info:
            decrypt_value("plaintext without prefix")
        assert "does not have encryption prefix" in str(exc_info.value)

    def test_decrypt_tampered_data_raises(self):
        key = base64.urlsafe_b64encode(os.urandom(32)).decode()
        os.environ["FIELD_ENCRYPTION_KEY"] = key
        _reset_key_cache()
        encrypted = encrypt_value("secret")
        tampered = encrypted[:-5] + "XXXXX"
        with pytest.raises(EncryptionError) as exc_info:
            decrypt_value(tampered)
        assert "Decryption failed" in str(exc_info.value)

    def test_wrong_key_raises_on_decrypt(self):
        key1 = base64.urlsafe_b64encode(os.urandom(32)).decode()
        key2 = base64.urlsafe_b64encode(os.urandom(32)).decode()
        os.environ["FIELD_ENCRYPTION_KEY"] = key1
        _reset_key_cache()
        encrypted = encrypt_value("secret")
        os.environ["FIELD_ENCRYPTION_KEY"] = key2
        _reset_key_cache()
        with pytest.raises(EncryptionError) as exc_info:
            decrypt_value(encrypted)
        assert "Decryption failed" in str(exc_info.value)


class TestMissingKey:
    def test_missing_key_raises_clear_error(self):
        _reset_key_cache()
        original_key = os.environ.pop("FIELD_ENCRYPTION_KEY", None)
        try:
            with pytest.raises(EncryptionError) as exc_info:
                encrypt_value("test")
            assert "FIELD_ENCRYPTION_KEY environment variable is not set" in str(exc_info.value)
        finally:
            _reset_key_cache()
            if original_key:
                os.environ["FIELD_ENCRYPTION_KEY"] = original_key