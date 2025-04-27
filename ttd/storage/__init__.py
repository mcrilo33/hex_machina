"""
Submodule for all storage logic.
Backed by pluggable storage implementations (e.g., TinyDB).
"""

from .base_storage import StorageService, TinyDBStorageService
from .ttd_storage import TTDStorage

__all__ = [
    "StorageService",
    "TinyDBStorageService",
    "TTDStorage",
]
