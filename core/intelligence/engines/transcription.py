import io
import requests
from abc import ABC, abstractmethod
from typing import Optional
from core.config import settings

class BaseTranscriptionEngine(ABC):
    @abstractmethod
    def transcribe(self, audio_buffer: io.BytesIO) -> Optional[str]:
        pass

class GroqTranscriptionEngine(BaseTranscriptionEngine):
    """
    Modular engine for Groq Speech-to-Text REST protocol (OpenAI-compatible).
    """
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.url = "https://api.groq.com/openai/v1/audio/transcriptions"
        self.model = settings.GROQ_STT_MODEL

    def transcribe(self, audio_buffer: io.BytesIO) -> Optional[str]:
        """
        Sends audio buffer to Groq STT and returns the transribed text.
        Returns None if transcription is empty or purely silence markers.
        """
        if not self.api_key:
            print("[!] Groq Transcription Error: API Key missing.")
            return None

        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        
        files = {
            "file": ("speech.wav", audio_buffer, "audio/wav"),
            "model": (None, self.model),
            "response_format": (None, "json")
        }

        try:
            response = requests.post(self.url, headers=headers, files=files, timeout=10)
            
            # Verification Gate
            if response.status_code != 200:
                print(f"[!] Groq STT Error: HTTP {response.status_code} - {response.text}")
                return None
            
            data = response.json()
            text = data.get("text", "").strip()

            # Content Validation
            # If text length < 2 or contains only common silence markers, return None
            # Groq sometimes returns "." or " " or silence labels for pure noise
            if len(text) < 2 or text.lower() in [".", "...", "[silence]", "[noise]", "(silence)"]:
                return None
            
            return text

        except Exception as e:
            print(f"[!] Groq STT Integration Exception: {e}")
            return None
