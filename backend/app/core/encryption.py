"""Encryption utilities for storing sensitive credentials."""

import base64
import hashlib

from cryptography.fernet import Fernet

from app.core.config import settings


def _get_fernet() -> Fernet:
    """Get Fernet instance using JWT secret as key base."""
    # Derive a 32-byte key from the JWT secret
    key = hashlib.sha256(settings.JWT_SECRET_KEY.encode()).digest()
    key_b64 = base64.urlsafe_b64encode(key)
    return Fernet(key_b64)


def encrypt_value(plaintext: str) -> str:
    """Encrypt a string value."""
    fernet = _get_fernet()
    return fernet.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a string value."""
    fernet = _get_fernet()
    return fernet.decrypt(ciphertext.encode()).decode()
