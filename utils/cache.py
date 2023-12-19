import json
import os


class Cache:
    """A simple cache that stores key-value pairs in a JSON file."""

    def __init__(self, path="cache.json"):
        self.path = path
        self.cache = None

        self.init()

    def init(self):
        if os.path.exists(self.path):
            self._load(self.path)
        else:
            self.cache = {}

    def get(self, key):
        if key in self.cache:
            return self.cache[key]
        return None

    def set(self, key, value):
        self.cache[key] = value
        self._save()

    def clear(self):
        self.cache = {}
        self._save()

    def _save(self):
        with open(self.path, "w") as f:
            json.dump(self.cache, f)

    def _load(self, path):
        with open(path, "r") as f:
            self.cache = json.load(f)
