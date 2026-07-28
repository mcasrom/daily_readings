import time
import random
import threading
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self, config):
        self.min_interval = config.get("min_interval", 900)
        self.max_retries = config.get("max_retries", 3)
        self.backoff_base = config.get("backoff_base", 2)
        self.jitter = config.get("jitter", True)
        self._last_hit = {}
        self._lock = threading.Lock()

    def wait_if_needed(self, source_url):
        with self._lock:
            last = self._last_hit.get(source_url, 0)
            elapsed = time.time() - last
            if elapsed < self.min_interval:
                wait = self.min_interval - elapsed
                if self.jitter:
                    wait += random.uniform(0, wait * 0.1)
                time.sleep(wait)
            self._last_hit[source_url] = time.time()

    def get_backoff(self, attempt):
        delay = self.backoff_base ** attempt
        if self.jitter:
            delay += random.uniform(0, delay * 0.5)
        return min(delay, 300)

    def should_retry(self, attempt, status_code=None):
        if attempt >= self.max_retries:
            return False
        if status_code and status_code < 500 and status_code != 429:
            return False
        return True


class FeedCache:
    def __init__(self, ttl=1800):
        self.ttl = ttl
        self._cache = {}
        self._lock = threading.Lock()

    def get(self, url):
        with self._lock:
            entry = self._cache.get(url)
            if entry and (time.time() - entry["time"]) < self.ttl:
                return entry["data"]
            return None

    def set(self, url, data):
        with self._lock:
            self._cache[url] = {"data": data, "time": time.time()}

    def invalidate(self, url):
        with self._lock:
            self._cache.pop(url, None)

    def clear(self):
        with self._lock:
            self._cache.clear()
