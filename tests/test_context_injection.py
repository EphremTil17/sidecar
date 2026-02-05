import pytest
from unittest.mock import MagicMock, patch
from core.intelligence.engines.groq_engine import GroqEngine
from core.intelligence.model import SidecarBrain
from core.ingestion.audio import AudioIngest
from core.intelligence.events import SidecarEventType

def test_groq_engine_context_injection():
    """Verify that transcription context is correctly injected into the Llama content block."""
    engine = GroqEngine(api_key="fake-key")
    engine.init_session("System Prompt")
    
    png_bytes = b"fake_image"
    additional_text = "What is this code doing?"
    
    with patch.object(engine.client.chat.completions, 'create') as mock_create:
        mock_create.return_value = [] 
        list(engine.stream_analysis(png_bytes, additional_text))
        
        last_msg = engine.messages[-1]
        assert last_msg['role'] == 'user'
        # Check for the [CONVERSATION TURN] tag which we use to inject the 'most recent turn'
        context_part = [p for p in last_msg['content'] if p.get('type') == 'text' and "[CONVERSATION TURN]:" in p.get('text', '')]
        assert len(context_part) > 0
        assert additional_text in context_part[0]['text']

def test_sidecar_brain_verbal_stream():
    """Verify that Verbal Turn (Vector T) triggers a follows-up completion without vision data."""
    brain = SidecarBrain(google_api_key="fake-key", groq_api_key="fake-key")
    mock_engine = MagicMock()
    brain.active_engine = mock_engine
    brain.active_engine.messages = []
    
    transcription = "Correct my last point: it should be O(n)."
    list(brain.analyze_verbal_stream(transcription))
    
    # Check that it appended to history and triggered completion
    assert len(brain.active_engine.messages) == 1
    assert "[CONVERSATION TURN]" in brain.active_engine.messages[0]['content']
    mock_engine._execute_chat_completion.assert_called_once()

def test_audio_ingest_persistence_logic():
    """Verify that the ingestion layer distinguishes between persistent context (P) and fresh intent (T)."""
    from unittest.mock import mock_open, MagicMock
    
    mock_file_content = "Test transcription content"
    mock_file = mock_open(read_data=mock_file_content)
    
    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", mock_file):
            ingest = AudioIngest(transcript_path="dummy.txt")
            
            # Case 1: Vector P (Persistent) - Should NOT truncate the file
            result = ingest.poll_for_transcript(clear=False)
            assert result == mock_file_content
            # Verify no truncate was called
            mock_file().truncate.assert_not_called()
            
            # Reset mock
            mock_file.reset_mock()
            mock_file.return_value.read.return_value = mock_file_content
            
            # Case 2: Vector T (Clear/Overwrite) - Should truncate the file in-place
            result = ingest.poll_for_transcript(clear=True)
            assert result == mock_file_content
            # Verify seek(0) and truncate(0) were called for in-place clearing
            mock_file().seek.assert_called_with(0)
            mock_file().truncate.assert_called_with(0)
