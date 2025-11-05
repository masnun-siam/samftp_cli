from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class Server:
    name: str
    url: str
    username: Optional[str] = None
    password: Optional[str] = None
    last_accessed: Optional[float] = None
    preferred_player: Optional[str] = None


@dataclass
class File:
    name: str
    url: str
    size: Optional[int] = None  # Size in bytes if available


@dataclass
class Folder:
    name: str
    url: str


@dataclass
class Bookmark:
    name: str
    server: str
    url: str
    timestamp: float


@dataclass
class CacheEntry:
    url: str
    timestamp: float
    folders: list
    files: list


@dataclass
class AppSession:
    """Runtime application state container."""
    selected_server: Optional[Server] = None
    selected_player: Optional[str] = None
    download_directory: Optional[str] = None
    history: list = field(default_factory=list)
    current_url: Optional[str] = None


# Utility functions
def format_file_size(size_bytes: int) -> str:
    """
    Convert bytes to human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Human-readable size string (e.g., "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def parse_url_path(url: str) -> list:
    """
    Extract path components from URL for breadcrumb display.

    Args:
        url: Full URL

    Returns:
        List of path components
    """
    from urllib.parse import urlparse, unquote

    parsed = urlparse(url)
    path = unquote(parsed.path)

    # Split path and filter out empty components
    components = [c for c in path.split('/') if c]

    return components 