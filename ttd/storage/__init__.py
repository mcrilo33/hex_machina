"""
Submodule for all storage logic.
Backed by pluggable storage implementations (e.g., TinyDB).
"""

from .base import StorageService, TinyDBStorageService
from .ttd import TTDStorage

__all__ = [
    "StorageService",
    "TinyDBStorageService",
    "TTDStorage",
]