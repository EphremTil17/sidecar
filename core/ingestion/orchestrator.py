from enum import Enum
from core.ingestion.audio_sensor import AudioSensor
from core.intelligence.transcription_service import TranscriptionService

class RecordingState(Enum):
    IDLE = "IDLE"
    RECORDING = "RECORDING"
    PROCESSING = "PROCESSING"

class RecordingOrchestrator:
    """
    Manages the stateful recording cycle for Vector T.
    Decouples sidecar.py from the low-level recording and transcription implementation.
    """
    def __init__(self, sensor: AudioSensor, transcription_service: TranscriptionService):
        self.sensor = sensor
        self.transcription_service = transcription_service
        self.state = RecordingState.IDLE

    def toggle(self):
        """Toggles the recording state. Returns the new state and transcribed text if processing finished."""
        if self.state == RecordingState.IDLE:
            self.sensor.start()
            self.state = RecordingState.RECORDING
            return self.state, None
        
        elif self.state == RecordingState.RECORDING:
            self.state = RecordingState.PROCESSING
            buffer = self.sensor.stop()
            
            # Use the dedicated transcription service
            text = self.transcription_service.transcribe(buffer)
            
            self.state = RecordingState.IDLE
            return self.state, text
        
        return self.state, None

    @property
    def is_idle(self):
        return self.state == RecordingState.IDLE

    @property
    def is_recording(self):
        return self.state == RecordingState.RECORDING
    
    @property
    def is_processing(self):
        return self.state == RecordingState.PROCESSING
