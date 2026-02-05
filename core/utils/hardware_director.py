import sounddevice as sd
from core.ingestion.screen import get_available_monitors
from core.utils.audio import get_wasapi_input_devices
from core.ui.cli import CLI

class HardwareDirector:
    """
    Handles monitor and audio device discovery, selection, and validation.
    """
    def select_hardware(self):
        """Interactive setup for hardware."""
        monitors = get_available_monitors()
        monitor_idx = CLI.select_monitor_menu(monitors)
        
        input_devices = get_wasapi_input_devices()
        selected_audio_id = CLI.select_audio_device_menu(input_devices)
        
        if selected_audio_id is not None:
            sd.default.device = (selected_audio_id, None)
            
        return monitor_idx, selected_audio_id

    def validate_cache(self, cache: dict) -> bool:
        """Checks if cached hardware is still available."""
        monitors = get_available_monitors()
        cached_mon = cache.get("monitor_index")
        if not any(m['index'] == cached_mon for m in monitors):
            return False

        input_devices = get_wasapi_input_devices()
        cached_audio = cache.get("audio_device_id")
        if cached_audio is not None and not any(d[0] == cached_audio for d in input_devices):
            return False

        return True

    def apply_settings(self, monitor_idx: int, audio_id: int):
        """Applies hardware settings without interaction."""
        if audio_id is not None:
            sd.default.device = (audio_id, None)
