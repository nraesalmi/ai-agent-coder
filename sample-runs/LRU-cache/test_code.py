import time
import pytest
from code import LRUCache  # replace 'code' with actual module name

def test_get_returns_value_when_key_exists_and_not_expired():
    cache = LRUCache(max_entries=2)
    cache.put("key1", "value1", ttl_seconds=5)
    result = cache.get("key1")
    assert result == "value1"

def test_get_returns_none_when_key_does_not_exist():
    cache = LRUCache(max_entries=2)
    result = cache.get("missing_key")
    assert result is None

def test_get_returns_none_when_key_expired():
    cache = LRUCache(max_entries=2)
    cache.put("key1", "value1", ttl_seconds=1)
    time.sleep(1.1)
    result = cache.get("key1")
    assert result is None

def test_get_updates_recency_of_key():
    cache = LRUCache(max_entries=2)
    cache.put("key1", "value1")
    cache.put("key2", "value2")
    # Access key1 to make it recently used
    _ = cache.get("key1")
    # Add new key3 to cause eviction of the least recently used (key2)
    cache.put("key3", "value3")
    assert cache.get("key1") == "value1"
    assert cache.get("key2") is None  # key2 should be evicted
    assert cache.get("key3") == "value3"

def test_get_with_no_ttl_key_never_expires():
    cache = LRUCache(max_entries=1)
    cache.put("perm_key", "perm_value")
    time.sleep(1)
    assert cache.get("perm_key") == "perm_value"