import io
import wave
import numpy as np
import sounddevice as sd
from typing import Optional

class AudioSensor:
    """
    High-performance audio capture engine using sounddevice.
    Captures 16kHz, Mono, 16-bit PCM directly to RAM.
    """
    def __init__(self, sample_rate: int = None, channels: int = 1):
        # Use settings if not provided
        from core.config import settings
        self.sample_rate = sample_rate or settings.AUDIO_SAMPLE_RATE
        self.channels = channels
        self.actual_sample_rate = self.sample_rate
        self.stream: Optional[sd.InputStream] = None
        self._buffer = []
        self._is_recording = False

    def _callback(self, indata, frames, time, status):
        """Non-blocking callback to collect audio frames."""
        if status:
            print(f"[!] Audio Source Status: {status}")
        
        if self._is_recording:
            audio_data = (np.clip(indata, -1, 1) * 32767).astype(np.int16)
            self._buffer.append(audio_data.copy())

    def start(self):
        """Initializes the InputStream using preferred rate or device default."""
        if self._is_recording:
            return

        self._buffer = []
        
        from core.utils.logger import logger
        try:
            # Attempt 1: Configured/Preferred Rate
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype='float32',
                callback=self._callback
            )
            self.actual_sample_rate = self.sample_rate
            logger.success(f"Audio Stream Active: [{sd.default.device[0]}] {sd.query_devices(sd.default.device[0], 'input')['name']} | WASAPI ({self.sample_rate}Hz)")
        except Exception:
            # Attempt 2: Device native default (Final Fallback)
            try:
                device_info = sd.query_devices(sd.default.device[0], 'input')
                native_rate = int(device_info['default_samplerate'])
                
                self.stream = sd.InputStream(
                    samplerate=native_rate,
                    channels=self.channels,
                    dtype='float32',
                    callback=self._callback
                )
                self.actual_sample_rate = native_rate
                logger.warning(f"Audio Hardware rejected {self.sample_rate}Hz. Using native: {native_rate}Hz.")
                logger.success(f"Audio Stream Active: [{sd.default.device[0]}] {device_info['name']} | WASAPI ({native_rate}Hz)")
            except Exception as e:
                logger.error(f"Audio Sensor Failure: Could not open microphone. {e}")
                raise e

        self.stream.start()
        self._is_recording = True

    def stop(self) -> io.BytesIO:
        """Closes the stream and returns the finalized BytesIO object containing WAV data."""
        if not self._is_recording:
            return io.BytesIO()

        self._is_recording = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

        if not self._buffer:
            return io.BytesIO()

        # Concatenate all chunks
        full_audio = np.concatenate(self._buffer, axis=0)
        
        # Write to in-memory WAV
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2) # 16-bit
            wf.setframerate(self.actual_sample_rate)
            wf.writeframes(full_audio.tobytes())
        
        buffer.seek(0)
        return buffer

    @property
    def is_recording(self):
        return self._is_recording
