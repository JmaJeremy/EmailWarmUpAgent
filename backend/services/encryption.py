"""
Encryption service for SMTP/IMAP passwords using Fernet symmetric encryption.
Passwords are encrypted at rest and decrypted only when needed for connection.
"""
import base64
import hashlib
from cryptography.fernet import Fernet
from config import settings


def _get_fernet() -> Fernet:
    """Derive a valid 32-byte Fernet key from the config key."""
    raw = settings.encryption_key.encode()
    key = base64.urlsafe_b64encode(hashlib.sha256(raw).digest())
    return Fernet(key)


def encrypt_password(plain_password: str) -> str:
    """Encrypt a plain-text password for storage."""
    f = _get_fernet()
    return f.encrypt(plain_password.encode()).decode()


def decrypt_password(encrypted_password: str) -> str:
    """Decrypt a stored encrypted password for use."""
    f = _get_fernet()
    return f.decrypt(encrypted_password.encode()).decode()
