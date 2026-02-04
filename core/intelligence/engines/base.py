from abc import ABC, abstractmethod

class BaseEngine(ABC):
    @abstractmethod
    def init_session(self, system_prompt):
        """Initializes or resets the chat session."""
        pass

    @abstractmethod
    def stream_analysis(self, png_bytes, additional_text=""):
        """Streams analysis of an image and optional text."""
        pass

    @abstractmethod
    def stream_pivot(self, skill_data, assembled_prompt):
        """Pivots the session to a new skill."""
        pass

    @abstractmethod
    def get_model_name(self):
        """Returns the human-readable name of the active model."""
        pass

    @abstractmethod
    def toggle_model(self):
        """Toggles between fast and deep models if applicable."""
        pass
