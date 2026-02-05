import io
import pytest
import requests
from unittest.mock import MagicMock, patch
from core.intelligence.engines.transcription import GroqTranscriptionEngine

@pytest.fixture
def engine():
    return GroqTranscriptionEngine(api_key="test_key")

def test_transcribe_success(engine):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"text": "Hello world transcription."}
    
    with patch("requests.post", return_value=mock_response):
        audio_buffer = io.BytesIO(b"fake wav data")
        result = engine.transcribe(audio_buffer)
        
        assert result == "Hello world transcription."

def test_transcribe_silence(engine):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"text": "."}
    
    with patch("requests.post", return_value=mock_response):
        audio_buffer = io.BytesIO(b"fake wav data")
        result = engine.transcribe(audio_buffer)
        
        assert result is None

def test_transcribe_error(engine):
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"
    
    with patch("requests.post", return_value=mock_response):
        audio_buffer = io.BytesIO(b"fake wav data")
        result = engine.transcribe(audio_buffer)
        
        assert result is None
