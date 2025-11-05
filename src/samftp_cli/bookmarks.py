import json
import time
from pathlib import Path
from typing import List, Optional
from platformdirs import user_config_dir
from .data_models import Bookmark


class BookmarkManager:
    """Manages user bookmarks for quick access to favorite directories."""

    def __init__(self):
        """Initialize bookmark manager."""
        self.config_dir = Path(user_config_dir("samftp-cli"))
        self.bookmarks_file = self.config_dir / "bookmarks.json"
        self._ensure_config_dir()
        self._bookmarks_cache = None

    def _ensure_config_dir(self):
        """Create config directory if it doesn't exist."""
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def _load_bookmarks(self) -> List[Bookmark]:
        """Load bookmarks from disk."""
        if self._bookmarks_cache is not None:
            return self._bookmarks_cache

        if not self.bookmarks_file.exists():
            self._bookmarks_cache = []
            return self._bookmarks_cache

        try:
            with open(self.bookmarks_file, 'r') as f:
                data = json.load(f)
                self._bookmarks_cache = [Bookmark(**item) for item in data]
                return self._bookmarks_cache
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load bookmarks: {e}")
            self._bookmarks_cache = []
            return self._bookmarks_cache

    def _save_bookmarks(self, bookmarks: List[Bookmark]):
        """Save bookmarks to disk."""
        try:
            data = [
                {
                    'name': b.name,
                    'server': b.server,
                    'url': b.url,
                    'timestamp': b.timestamp
                }
                for b in bookmarks
            ]
            with open(self.bookmarks_file, 'w') as f:
                json.dump(data, f, indent=2)
            self._bookmarks_cache = bookmarks
        except IOError as e:
            print(f"Error: Could not save bookmarks: {e}")

    def add_bookmark(self, name: str, server: str, url: str) -> bool:
        """
        Add a new bookmark.

        Args:
            name: User-friendly name for the bookmark
            server: Server name
            url: Full URL to the directory

        Returns:
            True if added successfully, False if name already exists
        """
        bookmarks = self._load_bookmarks()

        # Check if name already exists
        if any(b.name.lower() == name.lower() for b in bookmarks):
            return False

        bookmark = Bookmark(
            name=name,
            server=server,
            url=url,
            timestamp=time.time()
        )

        bookmarks.append(bookmark)
        self._save_bookmarks(bookmarks)
        return True

    def remove_bookmark(self, name: str) -> bool:
        """
        Remove a bookmark by name.

        Args:
            name: Name of the bookmark to remove

        Returns:
            True if removed, False if not found
        """
        bookmarks = self._load_bookmarks()
        original_count = len(bookmarks)

        bookmarks = [b for b in bookmarks if b.name.lower() != name.lower()]

        if len(bookmarks) < original_count:
            self._save_bookmarks(bookmarks)
            return True

        return False

    def get_bookmark(self, name: str) -> Optional[Bookmark]:
        """
        Get a bookmark by name.

        Args:
            name: Name of the bookmark

        Returns:
            Bookmark if found, None otherwise
        """
        bookmarks = self._load_bookmarks()
        for bookmark in bookmarks:
            if bookmark.name.lower() == name.lower():
                return bookmark
        return None

    def list_bookmarks(self) -> List[Bookmark]:
        """
        Get all bookmarks sorted by timestamp (most recent first).

        Returns:
            List of bookmarks
        """
        bookmarks = self._load_bookmarks()
        return sorted(bookmarks, key=lambda b: b.timestamp, reverse=True)

    def is_bookmarked(self, url: str) -> Optional[str]:
        """
        Check if a URL is bookmarked.

        Args:
            url: URL to check

        Returns:
            Bookmark name if found, None otherwise
        """
        bookmarks = self._load_bookmarks()
        for bookmark in bookmarks:
            if bookmark.url == url:
                return bookmark.name
        return None

    def update_bookmark(self, name: str, new_name: Optional[str] = None,
                       new_url: Optional[str] = None) -> bool:
        """
        Update an existing bookmark.

        Args:
            name: Current bookmark name
            new_name: New name (optional)
            new_url: New URL (optional)

        Returns:
            True if updated, False if not found
        """
        bookmarks = self._load_bookmarks()

        for bookmark in bookmarks:
            if bookmark.name.lower() == name.lower():
                if new_name:
                    # Check if new name already exists
                    if any(b.name.lower() == new_name.lower() and b.name != bookmark.name
                          for b in bookmarks):
                        return False
                    bookmark.name = new_name

                if new_url:
                    bookmark.url = new_url

                bookmark.timestamp = time.time()
                self._save_bookmarks(bookmarks)
                return True

        return False

    def get_bookmarks_by_server(self, server: str) -> List[Bookmark]:
        """
        Get all bookmarks for a specific server.

        Args:
            server: Server name

        Returns:
            List of bookmarks for the server
        """
        bookmarks = self._load_bookmarks()
        return [b for b in bookmarks if b.server == server]

    def clear_all_bookmarks(self) -> int:
        """
        Remove all bookmarks.

        Returns:
            Number of bookmarks removed
        """
        bookmarks = self._load_bookmarks()
        count = len(bookmarks)

        if count > 0:
            self._save_bookmarks([])

        return count

    def export_bookmarks(self, file_path: str) -> bool:
        """
        Export bookmarks to a JSON file.

        Args:
            file_path: Path to export file

        Returns:
            True if successful, False otherwise
        """
        bookmarks = self._load_bookmarks()

        try:
            data = [
                {
                    'name': b.name,
                    'server': b.server,
                    'url': b.url,
                    'timestamp': b.timestamp
                }
                for b in bookmarks
            ]
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except IOError as e:
            print(f"Error: Could not export bookmarks: {e}")
            return False

    def import_bookmarks(self, file_path: str, merge: bool = True) -> int:
        """
        Import bookmarks from a JSON file.

        Args:
            file_path: Path to import file
            merge: If True, merge with existing bookmarks; if False, replace

        Returns:
            Number of bookmarks imported
        """
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)

            imported = [Bookmark(**item) for item in data]

            if merge:
                existing = self._load_bookmarks()
                existing_names = {b.name.lower() for b in existing}

                # Only import bookmarks with unique names
                new_bookmarks = [b for b in imported
                               if b.name.lower() not in existing_names]

                all_bookmarks = existing + new_bookmarks
                self._save_bookmarks(all_bookmarks)
                return len(new_bookmarks)
            else:
                self._save_bookmarks(imported)
                return len(imported)

        except (IOError, json.JSONDecodeError, KeyError) as e:
            print(f"Error: Could not import bookmarks: {e}")
            return 0


# Global bookmark manager instance
_global_bookmark_manager = None


def get_bookmark_manager() -> BookmarkManager:
    """Get or create global bookmark manager instance."""
    global _global_bookmark_manager
    if _global_bookmark_manager is None:
        _global_bookmark_manager = BookmarkManager()
    return _global_bookmark_manager
