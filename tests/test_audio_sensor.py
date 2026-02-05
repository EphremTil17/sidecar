import io
import time
import wave
import pytest
import numpy as np
from core.ingestion.audio_sensor import AudioSensor

def test_audio_sensor_initialization():
    sensor = AudioSensor()
    assert sensor.sample_rate == 16000
    assert sensor.channels == 1
    assert not sensor.is_recording

def test_audio_sensor_recording_lifecycle():
    sensor = AudioSensor()
    
    # Start
    sensor.start()
    assert sensor.is_recording
    assert sensor.stream is not None
    
    # Wait a tiny bit to capture something (silence)
    time.sleep(0.5)
    
    # Stop
    buffer = sensor.stop()
    assert not sensor.is_recording
    assert sensor.stream is None
    assert isinstance(buffer, io.BytesIO)
    
    # Validate WAV content
    buffer.seek(0)
    with wave.open(buffer, 'rb') as wf:
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2 # 16-bit
        assert wf.getframerate() == 16000
        n_frames = wf.getnframes()
        assert n_frames > 0
