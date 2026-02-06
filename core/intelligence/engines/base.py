from abc import ABC, abstractmethod
from typing import Generator
from core.intelligence.events import SidecarEvent

class BaseEngine(ABC):
    @abstractmethod
    def init_session(self, system_prompt):
        """Initializes or resets the chat session."""
        pass

    @abstractmethod
    def stream_analysis(self, png_bytes: bytes, additional_text: str = "") -> Generator[SidecarEvent, None, None]:
        """Streams analysis events (text, status, etc.)"""
        pass

    @abstractmethod
    def stream_pivot(self, skill_data: dict, assembled_prompt: str) -> Generator[SidecarEvent, None, None]:
        """Pivots the session with event streaming."""
        pass

    @abstractmethod
    def get_model_name(self):
        """Returns the human-readable name of the active model."""
        pass

    @abstractmethod
    def toggle_model(self):
        """Toggles between fast and deep models if applicable."""
        pass

    @abstractmethod
    def add_user_message(self, content: str):
        """Adds a user message to the session history."""
        pass
