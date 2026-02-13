import dataclasses
from typing import List, Optional

@dataclasses.dataclass
class VaultItem:
    """Represents a single piece of visual context."""
    image_bytes: bytes
    label: str = "supporting_context"

class VisionVault:
    """
    Modular component for managing a stack of contextual images.
    Decouples context retention from inference logic.
    """
    def __init__(self, max_items: int = 5):
        self._items: List[VaultItem] = []
        self.max_items = max_items

    def add(self, image_bytes: bytes, label: str = "supporting_context"):
        """Adds a new image to the context stack."""
        if not image_bytes:
            return
            
        # Maintain a sliding window of context to prevent token bloat
        if len(self._items) >= self.max_items:
            self._items.pop(0)
            
        self._items.append(VaultItem(image_bytes=image_bytes, label=label))

    def get_context(self) -> List[VaultItem]:
        """Returns the current list of vaulted context items."""
        return self._items.copy()

    def clear(self):
        """Empties the vault."""
        self._items = []

    def __len__(self):
        return len(self._items)

    @property
    def has_context(self) -> bool:
        return len(self._items) > 0
