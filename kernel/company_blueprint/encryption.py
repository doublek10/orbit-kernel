"""
Encryption (Security Engine)

Symmetric encryption for anything the Blueprint stores that must never
sit in Postgres as plaintext: provider API credentials, webhook signing
secrets, refresh tokens (Financial Connections - the next Blueprint
section to be built on top of this module).

Deliberately narrow: this file only knows how to encrypt/decrypt bytes.
It has no opinion on *what* gets encrypted or *when* - that belongs to
whichever module owns the field (e.g. the future provider_connections
credential columns). Uses Fernet (AES-128-CBC + HMAC, authenticated) -
simple, well-audited, sufficient for symmetric at-rest encryption of
short secrets. Swap for envelope encryption with a KMS-backed key later
without changing any caller - the encrypt()/decrypt() signatures stay
the same.
"""

from cryptography.fernet import Fernet, InvalidToken

from shared.config import get_settings


class DecryptionError(ValueError):
    """Raised when a stored value can't be decrypted with the current key."""


def _fernet() -> Fernet:
    settings = get_settings()
    return Fernet(settings.blueprint_encryption_key.encode())


def encrypt_secret(plaintext: str) -> str:
    """Returns a urlsafe-base64 ciphertext string, safe to store in a text column."""
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise DecryptionError("Could not decrypt - wrong key or corrupted value") from exc
