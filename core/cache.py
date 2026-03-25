"""
core/cache.py — Thread-Safe In-Memory Cache with TTL
Pro-Level: Auto-expiring cache for membership, channels, reports, cooldowns.
"""
import threading
import time
from typing import Any, Dict, Optional, Callable
from dataclasses import dataclass, field


@dataclass
class CacheEntry:
    """Single cache entry with expiration timestamp."""
    value: Any
    expires_at: float
    created_at: float = field(default_factory=time.time)
    
    def is_expired(self) -> bool:
        return time.time() > self.expires_at


class TTLCache:
    """
    Thread-safe in-memory cache with automatic TTL expiration.
    Works like Redis but in-process. Zero external dependencies.
    """
    
    def __init__(self, default_ttl: int = 300):
        self._store: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self.default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Get value if exists and not expired."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if entry.is_expired():
                del self._store[key]
                return None
            return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set a value with optional custom TTL."""
        with self._lock:
            ttl = ttl if ttl is not None else self.default_ttl
            self._store[key] = CacheEntry(
                value=value,
                expires_at=time.time() + ttl
            )
    
    def delete(self, key: str) -> bool:
        """Delete a key. Returns True if existed."""
        with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False
    
    def clear(self) -> int:
        """Clear all entries. Returns count cleared."""
        with self._lock:
            count = len(self._store)
            self._store.clear()
            return count
    
    def cleanup_expired(self) -> int:
        """Remove all expired entries. Returns count removed."""
        with self._lock:
            expired_keys = [
                k for k, v in self._store.items() if v.is_expired()
            ]
            for key in expired_keys:
                del self._store[key]
            return len(expired_keys)
    
    def get_or_set(self, key: str, factory: Callable, ttl: Optional[int] = None) -> Any:
        """Get cached value or compute and cache it."""
        value = self.get(key)
        if value is not None:
            return value
        value = factory()
        self.set(key, value, ttl)
        return value
    
    def exists(self, key: str) -> bool:
        """Check if key exists and is not expired."""
        return self.get(key) is not None
    
    def keys(self) -> list:
        """Get all non-expired keys."""
        with self._lock:
            self.cleanup_expired()
            return list(self._store.keys())
    
    def size(self) -> int:
        """Get count of non-expired entries."""
        with self._lock:
            self.cleanup_expired()
            return len(self._store)
    
    def __len__(self) -> int:
        return self.size()
    
    def __contains__(self, key: str) -> bool:
        return self.exists(key)


# ══════════════════════════════════════════════════════════════
#                     GLOBAL CACHE INSTANCES
# ══════════════════════════════════════════════════════════════

# Cache: Channel list (rarely changes, cache 10 min)
channel_cache = TTLCache(default_ttl=600)

# Cache: User membership status (changes when user joins/leaves)
membership_cache = TTLCache(default_ttl=300)

# Cache: Generated reports (expire after 30 min)
report_cache = TTLCache(default_ttl=1800)

# Cache: User search cooldowns (short TTL)
cooldown_cache = TTLCache(default_ttl=10)

# Cache: Rate limit tracking
rate_limit_cache = TTLCache(default_ttl=60)

# Global report storage (for pagination across callbacks)
# This is separate from report_cache for direct dict access in callbacks
global_report_cache: Dict[str, list] = {}
