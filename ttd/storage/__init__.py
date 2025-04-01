"""
Submodule for all storage logic.
Backed by pluggable storage implementations (e.g., TinyDB).
"""

from .text_file_manager import TextFileManager
from .model_manager import ModelManager
from .base_storage import StorageService, TinyDBStorageService
from .ttd_storage import TTDStorage

__all__ = [
    "TextFileManager",
    "ModelManager",
    "StorageService",
    "TinyDBStorageService",
    "TTDStorage",
]