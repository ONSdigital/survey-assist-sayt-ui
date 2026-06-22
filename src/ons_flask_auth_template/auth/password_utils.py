"""Password hashing helpers."""

from __future__ import annotations

from werkzeug.security import check_password_hash, generate_password_hash

SUPPORTED_HASH_PREFIXES = ("pbkdf2:", "scrypt:", "argon2:")


def hash_password(password: str) -> str:
    """Hash a plain text password.

    Args:
        password: Plain text password to hash.

    Returns:
        str: Werkzeug-compatible password hash.
    """
    return generate_password_hash(password)


def verify_password(stored_hash: str, candidate_password: str) -> bool:
    """Verify a candidate password against a stored hash.

    Args:
        stored_hash: Persisted password hash value.
        candidate_password: Plain text password supplied by the user.

    Returns:
        bool: True when the candidate password matches the stored hash.
    """
    if not stored_hash.startswith(SUPPORTED_HASH_PREFIXES):
        return False
    return check_password_hash(stored_hash, candidate_password)
