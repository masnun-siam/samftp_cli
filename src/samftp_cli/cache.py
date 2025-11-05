import json
import hashlib
import time
from pathlib import Path
from typing import List, Optional, Tuple
from platformdirs import user_cache_dir
from .data_models import Folder, File, CacheEntry


class CacheManager:
    """Manages directory listing cache with TTL expiration."""

    def __init__(self, ttl_seconds: int = 300):
        """
        Initialize cache manager.

        Args:
            ttl_seconds: Time-to-live for cache entries in seconds (default: 5 minutes)
        """
        self.ttl_seconds = ttl_seconds
        self.cache_dir = Path(user_cache_dir("samftp-cli"))
        self.cache_file = self.cache_dir / "directory_cache.json"
        self._ensure_cache_dir()
        self._memory_cache = {}

    def _ensure_cache_dir(self):
        """Create cache directory if it doesn't exist."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _url_to_hash(self, url: str) -> str:
        """Convert URL to hash for cache key."""
        return hashlib.sha256(url.encode()).hexdigest()

    def _load_cache_from_disk(self) -> dict:
        """Load cache from disk."""
        if not self.cache_file.exists():
            return {}

        try:
            with open(self.cache_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def _save_cache_to_disk(self, cache_data: dict):
        """Save cache to disk."""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
        except IOError as e:
            print(f"Warning: Could not save cache to disk: {e}")

    def _is_expired(self, timestamp: float) -> bool:
        """Check if cache entry is expired."""
        return (time.time() - timestamp) > self.ttl_seconds

    def get_cached_listing(self, url: str) -> Optional[Tuple[List[Folder], List[File]]]:
        """
        Retrieve cached directory listing if not expired.

        Args:
            url: The directory URL

        Returns:
            Tuple of (folders, files) if cached and not expired, None otherwise
        """
        url_hash = self._url_to_hash(url)

        # Check memory cache first
        if url_hash in self._memory_cache:
            entry = self._memory_cache[url_hash]
            if not self._is_expired(entry['timestamp']):
                folders = [Folder(**f) for f in entry['folders']]
                files = [File(**f) for f in entry['files']]
                return folders, files
            else:
                # Remove expired entry from memory
                del self._memory_cache[url_hash]

        # Check disk cache
        cache_data = self._load_cache_from_disk()
        if url_hash in cache_data:
            entry = cache_data[url_hash]
            if not self._is_expired(entry['timestamp']):
                # Load into memory cache
                self._memory_cache[url_hash] = entry
                folders = [Folder(**f) for f in entry['folders']]
                files = [File(**f) for f in entry['files']]
                return folders, files
            else:
                # Remove expired entry from disk
                del cache_data[url_hash]
                self._save_cache_to_disk(cache_data)

        return None

    def cache_listing(self, url: str, folders: List[Folder], files: List[File]):
        """
        Cache directory listing.

        Args:
            url: The directory URL
            folders: List of folders
            files: List of files
        """
        url_hash = self._url_to_hash(url)
        entry = {
            'url': url,
            'timestamp': time.time(),
            'folders': [{'name': f.name, 'url': f.url} for f in folders],
            'files': [{'name': f.name, 'url': f.url} for f in files]
        }

        # Update memory cache
        self._memory_cache[url_hash] = entry

        # Update disk cache
        cache_data = self._load_cache_from_disk()
        cache_data[url_hash] = entry
        self._save_cache_to_disk(cache_data)

    def invalidate_cache(self, url: str):
        """
        Invalidate cache for a specific URL.

        Args:
            url: The directory URL to invalidate
        """
        url_hash = self._url_to_hash(url)

        # Remove from memory
        if url_hash in self._memory_cache:
            del self._memory_cache[url_hash]

        # Remove from disk
        cache_data = self._load_cache_from_disk()
        if url_hash in cache_data:
            del cache_data[url_hash]
            self._save_cache_to_disk(cache_data)

    def clear_all_cache(self):
        """Clear all cache entries."""
        self._memory_cache.clear()

        if self.cache_file.exists():
            try:
                self.cache_file.unlink()
            except IOError as e:
                print(f"Warning: Could not delete cache file: {e}")

    def get_cache_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats (size, entry count, etc.)
        """
        cache_data = self._load_cache_from_disk()
        total_entries = len(cache_data)
        expired_entries = sum(1 for entry in cache_data.values()
                            if self._is_expired(entry['timestamp']))
        valid_entries = total_entries - expired_entries

        cache_size = 0
        if self.cache_file.exists():
            cache_size = self.cache_file.stat().st_size

        return {
            'total_entries': total_entries,
            'valid_entries': valid_entries,
            'expired_entries': expired_entries,
            'cache_size_bytes': cache_size,
            'cache_size_kb': cache_size / 1024,
            'cache_location': str(self.cache_file),
            'ttl_seconds': self.ttl_seconds
        }

    def cleanup_expired(self):
        """Remove all expired entries from cache."""
        cache_data = self._load_cache_from_disk()
        cleaned_data = {
            url_hash: entry for url_hash, entry in cache_data.items()
            if not self._is_expired(entry['timestamp'])
        }

        removed_count = len(cache_data) - len(cleaned_data)
        if removed_count > 0:
            self._save_cache_to_disk(cleaned_data)

        return removed_count


# Global cache instance (can be configured)
_global_cache = None


def get_cache_manager(ttl_seconds: int = 300) -> CacheManager:
    """Get or create global cache manager instance."""
    global _global_cache
    if _global_cache is None:
        _global_cache = CacheManager(ttl_seconds)
    return _global_cache
