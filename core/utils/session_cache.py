import json
from pathlib import Path


class SessionCache:
    """
    Handles JSON-based persistence of session configuration data.
    """

    CACHE_FILE = Path(".session_cache.json")

    @classmethod
    def save(cls, config: dict):
        """Saves session configuration to a JSON file."""
        try:
            with cls.CACHE_FILE.open("w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            print(f"[!] Error saving cache: {e}")

    @classmethod
    def load(cls) -> dict:
        """Loads session configuration from a JSON file."""
        if not cls.CACHE_FILE.exists():
            return {}
        try:
            with cls.CACHE_FILE.open(encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[!] Error loading cache: {e}")
            return {}

    @classmethod
    def clear(cls):
        """Removes the cached session file."""
        if cls.CACHE_FILE.exists():
            cls.CACHE_FILE.unlink()
