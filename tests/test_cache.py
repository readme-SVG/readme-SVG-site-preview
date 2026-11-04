import unittest
from unittest.mock import patch

from api.cache import TTLCache


class CacheTests(unittest.TestCase):
    def test_expiry_and_lru_eviction(self):
        cache = TTLCache(max_entries=2, ttl=10)
        with patch("api.cache.time.monotonic", return_value=100):
            cache.set("a", 1)
            cache.set("b", 2)
            cache.get("a")
            cache.set("c", 3)
        with patch("api.cache.time.monotonic", return_value=100):
            self.assertEqual(cache.get("a"), 1)
            self.assertIsNone(cache.get("b"))
        with patch("api.cache.time.monotonic", return_value=111):
            self.assertIsNone(cache.get("a"))

    def test_byte_budget_and_oversized_values(self):
        cache = TTLCache(max_entries=10, ttl=10, max_bytes=10)
        cache.set("a", "x", size=6)
        cache.set("b", "y", size=6)
        self.assertIsNone(cache.get("a"))
        self.assertEqual(cache.get("b"), "y")
        cache.set("huge", "z", size=11)
        self.assertIsNone(cache.get("huge"))
        self.assertEqual(cache._bytes, 6)


if __name__ == "__main__":
    unittest.main()
