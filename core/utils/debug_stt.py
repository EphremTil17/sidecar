import os
import sys
from colorama import init, Fore, Style
from core.config import settings
from core.ingestion.audio_sensor import AudioSensor
from core.ingestion.orchestrator import RecordingOrchestrator, RecordingState
from core.intelligence.transcription_service import TranscriptionService
from core.drivers.hotkeys import HotkeyManager
from core.utils.audio import select_audio_device_cli

# Initialize colorama
init(autoreset=True)

class STTDebugger:
    def __init__(self):
        self.transcription_service = TranscriptionService(settings.GROQ_API_KEY)
        self.sensor = AudioSensor()
        self.recorder = RecordingOrchestrator(self.sensor, self.transcription_service)

    def print_banner(self):
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.CYAN}       SIDECAR AI: GROQ STT DEBUGGER (v3.0)")
        print(f"{Fore.CYAN}   (High-Performance Modular Implementation)")
        print(f"{Fore.CYAN}{'='*60}\n")

    def handle_hotkey(self):
        new_state, audio_text = self.recorder.toggle()

        if new_state == RecordingState.RECORDING:
            print(f"\r{Fore.RED}[●] RECORDING... {Fore.WHITE}(Press Ctrl+Alt+Shift+T to stop)          ", end="", flush=True)
        
        elif self.recorder.is_processing:
            # Note: The toggle() returns text when it finishes processing
            # In RecordingOrchestrator, the state goes RECORDING -> PROCESSING -> IDLE
            # But the toggle logic I wrote in orchestrator.py:
            # if state == RECORDING: state = PROCESSING, transcribe, state = IDLE, return IDLE, text
            pass # The text is handled below

        if new_state == RecordingState.IDLE:
             if audio_text:
                print(f"\n\n{Fore.GREEN}TRANSCRIPTION:")
                print(f"{Style.BRIGHT}{Fore.WHITE}\"{audio_text}\"")
                print(f"\n{Fore.BLUE}{'-'*40}")
                print(f"{Fore.YELLOW}[Ready] {Fore.WHITE}Press Ctrl+Alt+Shift+T to record again.")
             else:
                print(f"\n\n{Fore.RED}[!] No speech recognized or silence detected.")
                print(f"{Fore.YELLOW}[Ready] {Fore.WHITE}Press Ctrl+Alt+Shift+T to record again.")

    def run(self):
        self.print_banner()
        
        if not settings.GROQ_API_KEY:
            print(f"{Fore.RED}[!] Error: GROQ_API_KEY not found in .env")
            return

        if select_audio_device_cli() is None:
            return

        hk = HotkeyManager()
        print(f"\n{Fore.GREEN}[+] STT Debugger Active.")
        print(f"{Fore.WHITE}Trigger: {Fore.CYAN}Ctrl + Alt + Shift + T")
        print(f"{Fore.WHITE}Status: {Fore.GREEN}READY\n")
        
        hk.register_hotkey(1, settings.VK_T, self.handle_hotkey)
        
        try:
            hk.listen(exit_callback=lambda: print(f"\n{Fore.YELLOW}[!] Shutting down context..."))
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    if os.name != 'nt':
        print("This debugger requires Windows for hotkey support.")
        sys.exit(1)
        
    debugger = STTDebugger()
    debugger.run()
