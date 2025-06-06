"""Hashing utilities."""
import hashlib


def sha256_key(text: str) -> str:
    """Generate a SHA-256 hash for a given input string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
