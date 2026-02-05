import json
import os
from core.config import settings

class SessionCache:
    """
    Handles persistence of the last used session configurations.
    """
    CACHE_FILE = os.path.join(settings.PROJECT_ROOT, ".session_cache.json")

    @classmethod
    def save(cls, config: dict):
        """Saves session configuration to a JSON file."""
        try:
            with open(cls.CACHE_FILE, 'w') as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            print(f"[!] Warning: Failed to save session cache: {e}")

    @classmethod
    def load(cls) -> dict:
        """Loads session configuration from a JSON file."""
        if not os.path.exists(cls.CACHE_FILE):
            return {}
        try:
            with open(cls.CACHE_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"[!] Warning: Failed to load session cache: {e}")
            return {}

    @classmethod
    def clear(cls):
        """Removes the cached session file."""
        if os.path.exists(cls.CACHE_FILE):
            os.remove(cls.CACHE_FILE)
