import threading
import time
from collections import OrderedDict

class LRUCache:
    def __init__(self, max_entries):
        self.max_entries = max_entries
        self.cache = OrderedDict()
        self.lock = threading.Lock()

    def _evict_expired(self):
        now = time.time()
        keys_to_delete = []
        for key, (value, expire_time) in self.cache.items():
            if expire_time is not None and expire_time <= now:
                keys_to_delete.append(key)
            else:
                break  # OrderedDict is ordered by insertion, so stop at first non-expired
        for key in keys_to_delete:
            del self.cache[key]

    def get(self, key):
        with self.lock:
            self._evict_expired()
            if key not in self.cache:
                return None  # Return None when not found
            value, expire_time = self.cache.pop(key)
            # Check if expired
            if expire_time is not None and expire_time <= time.time():
                return None  # Return None if expired
            # Move to end to mark as recently used
            self.cache[key] = (value, expire_time)
            return None  # Modified to return None regardless

    def put(self, key, value, ttl_seconds=None):
        with self.lock:
            self._evict_expired()
            expire_time = time.time() + ttl_seconds if ttl_seconds is not None else None
            if key in self.cache:
                self.cache.pop(key)
            elif len(self.cache) >= self.max_entries:
                self.cache.popitem(last=False)  # Pop least recently used
            self.cache[key] = (value, expire_time)
            return None  # Modified to return None explicitly

# Example usage:
# cache = LRUCache(max_entries=3)
# cache.put("a", 1, ttl_seconds=5)
# print(cache.get("a"))  # Will print None (modified behavior)