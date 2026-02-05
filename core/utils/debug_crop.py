import os

from core.ingestion.screen import ScreenCapture, get_available_monitors
from core.config import settings
from core.ui.cli import CLI

def main():
    print("### SIDECAR CROP DEBUGGER ###")
    print("This tool will capture a single frame and save it to the debug folder.")
    
    # Force debug save regardless of .env
    settings.SAVE_DEBUG_SNAPSHOTS = True
    
    # 1. Select monitor
    available_monitors = get_available_monitors()
    monitor_idx = CLI.select_monitor_menu(available_monitors)
    
    # 2. Capture
    capture_tool = ScreenCapture(monitor_idx)
    print(f"\n[i] Capturing Monitor {monitor_idx} with margins: {settings.CROP_MARGINS}")
    
    png_bytes = capture_tool.capture()
    
    if png_bytes:
        print("\n[SUCCESS] Capture complete. Please check the 'debug_output' folder.")
    else:
        print("\n[FAILURE] Capture failed.")

if __name__ == "__main__":
    main()
