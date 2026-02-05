from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Dict, Any, List

class SidecarEventType(Enum):
    TEXT_CHUNK = auto()
    STATUS = auto()
    ERROR = auto()
    FINISH = auto()

@dataclass
class SidecarEvent:
    event_type: SidecarEventType
    content: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
