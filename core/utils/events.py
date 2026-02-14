from enum import Enum, auto
from PyQt6.QtCore import QObject, pyqtSignal

class AppState(Enum):
    """
    Formal state definitions for the SidecarAI engine.
    Encapsulates the lifecycle and operational status of the app.
    """
    INITIALIZING = auto()
    IDLE = auto()
    RECORDING = auto()
    THINKING = auto()
    ERROR = auto()
    SHUTTING_DOWN = auto()

class AppEvent(Enum):
    """
    Event identifiers for the Decoupled Event Bus.
    """
    TRIGGER_PIXEL = auto()
    TRIGGER_TALK = auto()
    TRIGGER_INGEST = auto()
    
    UI_FOCUS_TOGGLE = auto()
    UI_FONT_SCALE = auto() # int: delta
    UI_MOVE = auto() # tuple: (dx, dy)
    UI_SCROLL = auto() # int: delta
    
    INTELLIGENCE_TOGGLE_MODEL = auto()
    INTELLIGENCE_SWITCH_ENGINE = auto()
    INTELLIGENCE_SWITCH_SKILL = auto()

    AGENT_STATUS_UPDATE = auto() # str: message
    AGENT_CHUNK_UPDATE = auto() # tuple: (text, type)
    AGENT_HEARTBEAT = auto()
    
    SYSTEM_SHUTDOWN = auto()

class AppEventBus(QObject):
    """
    Centralized Signal-Bus for the SidecarAI architecture.
    Acts as a Pub/Sub hub to decouple components.
    """
    # Using a single generic signal for now to keep it clean, 
    # but we can specialize if throughput becomes an issue.
    # Pattern: signal_name(AppEvent, Optional[AnyPayload])
    dispatch = pyqtSignal(object, object) 

    _instance = None

    @classmethod
    def instance(cls):
        """Singleton access for global visibility."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def publish(self, event: AppEvent, payload=None):
        """Publishes an event to all subscribers."""
        self.dispatch.emit(event, payload)

# Global Access Handle
bus = AppEventBus.instance()
