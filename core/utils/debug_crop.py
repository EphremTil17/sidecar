import os
import sys
from datetime import datetime

# Adjust path for standalone execution from project root
sys.path.append(os.getcwd())

from core.ingestion.screen import ScreenCapture, get_available_monitors
from core.config import settings
from core.ui.cli import CLI

def main():
    """
    Standalone utility to verify screen capture geometry and crop margins.
    Saves a timestamped PNG to 'debug_snapshots/' for visual inspection.
    """
    print("\n" + "="*50)
    print("### SIDECAR VISUAL CROP DEBUGGER ###")
    print("="*50)
    
    # 1. Force state for standalone debug
    settings.SAVE_DEBUG_SNAPSHOTS = True
    if not hasattr(settings, 'DEBUG_DIR'):
        settings.DEBUG_DIR = os.path.join(os.getcwd(), "debug_snapshots")
    
    # 2. Monitor Selection
    available = get_available_monitors()
    print(f"\n[i] Detected {len(available)} monitor(s).")
    
    # Use the existing CLI menu if available, otherwise fallback to simple input
    try:
        monitor_idx = CLI.select_monitor_menu(available)
    except Exception:
        for mon in available:
            print(mon)
        print("\nEnter monitor index to test: ", end="")
        monitor_idx = int(input().strip())

    # 3. Capture Execution
    print(f"\n[i] Initializing capture for Monitor {monitor_idx}...")
    print(f"[i] Applied Margins: {settings.CROP_MARGINS}")
    
    capture_tool = ScreenCapture(monitor_idx)
    png_bytes = capture_tool.capture()
    
    if png_bytes:
        # The ScreenCapture.capture() method handles the saving if SAVE_DEBUG_SNAPSHOTS is True
        print("\n" + "="*50)
        print(f"[SUCCESS] Frame captured and serialized.")
        print(f"[i] Destination: {settings.DEBUG_DIR}")
        print("Please open the PNG to verify your work-area framing.")
        print("="*50 + "\n")
    else:
        print("\n[!] CRITICAL: Capture failed. Verify monitor connectivity and permissions.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[i] Debugging session aborted.")
        sys.exit(0)
    except Exception as e:
        print(f"\n[!] Debug Tool Error: {e}")
        sys.exit(1)
