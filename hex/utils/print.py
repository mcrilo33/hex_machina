"""Printing utilities."""
from typing import Any
from rich.console import Console
from rich.pretty import Pretty

def truncate_nested(obj: Any, max_len: int = 100) -> Any:
    """Recursively truncate long strings in nested dicts/lists."""
    if isinstance(obj, dict):
        return {k: truncate_nested(v, max_len) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [truncate_nested(v, max_len) for v in obj]
    elif isinstance(obj, str) and len(obj) > max_len:
        return obj[:max_len] + "..."
    return obj

def safe_pretty_print(obj: Any, max_str_len: int = 80, max_width: int = 90) -> None:
    """Pretty print any object with truncation and width control using Rich."""
    truncated = truncate_nested(obj, max_len=max_str_len)
    console = Console(width=max_width)
    console.print(Pretty(truncated, expand_all=True))