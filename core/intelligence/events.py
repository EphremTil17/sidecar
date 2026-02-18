from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class SidecarEventType(Enum):
    TEXT_CHUNK = auto()
    THOUGHT_CHUNK = auto()
    STATUS = auto()
    ERROR = auto()
    FINISH = auto()


@dataclass
class SidecarEvent:
    event_type: SidecarEventType
    content: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
