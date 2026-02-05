import io
from typing import Optional
from core.intelligence.engines.transcription import GroqTranscriptionEngine

class TranscriptionService:
    """
    Dedicated service for handling audio transcription (STT).
    Decouples transcription from the main LLM orchestration (SidecarBrain).
    """
    def __init__(self, groq_api_key: str = None):
        self.groq_api_key = groq_api_key
        # Initialize transcription engine (Default to Groq for v3.0 Pulse)
        self.engine = GroqTranscriptionEngine(groq_api_key) if groq_api_key else None

    def transcribe(self, audio_buffer: io.BytesIO) -> Optional[str]:
        """Sends audio buffer to the active transcription engine."""
        if not self.engine:
            print("[!] Transcription Error: No engine initialized (check API keys).")
            return None
        return self.engine.transcribe(audio_buffer)
