import ctypes
import mss
import mss.tools
import os
import sys
import time
import subprocess
from google import genai
from google.genai import types
from ctypes import wintypes
from dotenv import load_dotenv
from utils import monitor_utils  # Custom module for monitor detection

# --- CONFIGURATION ---
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY") 
ENV_MONITOR_INDEX = os.getenv("SIDECAR_MONITOR_INDEX")

CROP_MARGINS = {"top": 120, "bottom": 40, "left": 0, "right": 0}

# Hotkeys
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
VK_P = 0x50 # 'P' for Process
VK_M = 0x4D # 'M' for Model Toggle

# --- STATE ---
# Toggle state: True = Pro/Reasoning, False = Flash
USE_PRO_MODEL = False 
MONITOR_INDEX = 1 # Default, will be updated in main

# --- INITIALIZATION ---
if not API_KEY:
    print("[CRITICAL] GOOGLE_API_KEY not found in .env file.")
    sys.exit(1)

# Initialize the new GenAI Client
client = genai.Client(api_key=API_KEY)

def load_context():
    """Reads the system prompt from context.txt"""
    try:
        with open("context.txt", "r") as f:
            return f.read()
    except FileNotFoundError:
        return "You are a helpful visual assistant."

def get_monitor_index():
    """
    Determines which monitor to use.
    Priority:
    1. SIDECAR_MONITOR_INDEX in .env
    2. User selection via interactive prompt
    3. Auto-detect Primary (Fallback)
    """
    available = monitor_utils.list_monitors()
    
    # 1. Check Env Var
    if ENV_MONITOR_INDEX:
        try:
            idx = int(ENV_MONITOR_INDEX)
            # Verify it exists
            for mon in available:
                if mon['index'] == idx:
                    return idx
            print(f"[!] Warning: Configured monitor index {idx} not found.")
        except ValueError:
            print("[!] Warning: Invalid SIDECAR_MONITOR_INDEX format.")

    # 2. Interactive Selection
    print("\n--- Available Monitors ---")
    primary_idx = 1
    for mon in available:
        tag = " (Primary)" if mon['primary'] else ""
        if mon['primary']: primary_idx = mon['index']
        print(f"[{mon['index']}] {mon['name']} [{mon['res']}] {tag}")
    
    print("\nSelect Monitor Index (or press Enter for Primary): ", end="")
    try:
        choice = input().strip()
        if not choice:
            return primary_idx # Default
        
        choice_idx = int(choice)
        # Validate
        for mon in available:
            if mon['index'] == choice_idx:
                print(f"[i] Tip: Add SIDECAR_MONITOR_INDEX={choice_idx} to .env to skip this.")
                return choice_idx
        
        print(f"[!] Invalid selection. Defaulting to Primary ({primary_idx}).")
        return primary_idx
        
    except ValueError:
        print(f"[!] Invalid input. Defaulting to Primary ({primary_idx}).")
        return primary_idx

def capture_screen_bytes():
    """Captures monitor 1 and crops it, returning raw PNG bytes."""
    with mss.mss() as sct:
        try:
            mon = sct.monitors[MONITOR_INDEX]
        except IndexError:
            print(f"[!] Error: Monitor {MONITOR_INDEX} not found.")
            return None

        # Calculate crop geometry
        bbox = {
            "top": mon["top"] + CROP_MARGINS["top"],
            "left": mon["left"] + CROP_MARGINS["left"],
            "width": mon["width"] - CROP_MARGINS["left"] - CROP_MARGINS["right"],
            "height": mon["height"] - CROP_MARGINS["top"] - CROP_MARGINS["bottom"],
            "mon": MONITOR_INDEX
        }
        
        # Grab the data
        sct_img = sct.grab(bbox)
        
        # Convert to PNG bytes
        return mss.tools.to_png(sct_img.rgb, sct_img.size)

def process_request():
    """Handles the capture and API call sequence."""
    global USE_PRO_MODEL
    
    # 1. Capture
    print("\n[O] Capturing...", end="", flush=True)
    png_bytes = capture_screen_bytes()
    if not png_bytes:
        return

    # 2. Prepare Prompt & Config
    system_prompt = load_context()
    
    if USE_PRO_MODEL:
        model_id = "models/gemini-3-pro-preview"
        print(" (PRO/THINKING)", end="\r", flush=True)
        # Gemini 3 Pro Thinking Config
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=1.0, 
            thinking_config=types.ThinkingConfig(include_thoughts=True, thinking_level="low")
        )
    else:
        model_id = "models/gemini-flash-latest"
        print(" (FLASH)", end="\r", flush=True)
        # Standard Config
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=1.0
        )

    print("\n Analyzing...", end="\r", flush=True)

    # 3. Call API
    try:
        # Create image part from bytes
        image_part = types.Part.from_bytes(data=png_bytes, mime_type="image/png")
        
        # Generate Content Stream
        response_stream = client.models.generate_content_stream(
            model=model_id,
            contents=["Analyze this view.", image_part],
            config=config
        )

        print(" " * 30, end="\r") # Clear "Analyzing..."
        print("> ", end="")
        
        # 4. Stream Output
        for chunk in response_stream:
            if chunk.text:
                print(chunk.text, end="", flush=True)
        print("\n")
        
    except Exception as e:
        print(f"\n[!] API Error: {e}")

def toggle_model():
    global USE_PRO_MODEL
    USE_PRO_MODEL = not USE_PRO_MODEL
    mode_str = "PRO (Thinking)" if USE_PRO_MODEL else "FLASH (Fast)"
    print(f"\n[i] Switched Model to: {mode_str}")

def kill_conflicting_instances():
    """Finds and kills other running instances of this script using PowerShell."""
    current_pid = os.getpid()
    print(f"[debug] Current PID: {current_pid}")
    try:
        # PowerShell command to find python processes running main.py
        ps_cmd = (
            "Get-CimInstance Win32_Process | "
            "Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -like '*main.py*' } | "
            "Select-Object -ExpandProperty ProcessId"
        )
        
        creation_flags = 0x08000000 if os.name == 'nt' else 0
        output = subprocess.check_output(
            ["powershell", "-Command", ps_cmd], 
            creationflags=creation_flags
        )
        
        pids = [int(p) for p in output.decode().split() if p.strip().isdigit()]
        killed_any = False
        for pid in pids:
            if pid != current_pid:
                print(f"[i] Terminating conflicting instance (PID: {pid})...")
                subprocess.run(f"taskkill /F /PID {pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                killed_any = True
        
        if killed_any:
            print("[i] Cleanup complete. Waiting 1s for release...")
            time.sleep(1)
            
    except Exception as e:
        print(f"[!] Warning: Failed to cleanup instances: {e}")

def main():
    global MONITOR_INDEX
    
    # Select monitor FIRST
    MONITOR_INDEX = get_monitor_index()
    
    print(f"### SIDECLAR AI INITIALIZED ###")
    print(f"Target: Monitor {MONITOR_INDEX}")
    print("Commands (Stealth):")
    print("  [P]rocess View: Ctrl + Alt + Shift + P")
    print("  [M]odel Toggle: Ctrl + Alt + Shift + M")
    print(f"Current Mode: {'PRO' if USE_PRO_MODEL else 'FLASH'}")

    user32 = ctypes.windll.user32
    
    # Try Register Hotkeys with Retry Logic
    for attempt in range(2):
        success_p = user32.RegisterHotKey(None, 1, MOD_CONTROL | MOD_ALT | MOD_SHIFT, VK_P)
        success_m = user32.RegisterHotKey(None, 2, MOD_CONTROL | MOD_ALT | MOD_SHIFT, VK_M)
        
        if success_p and success_m:
            break # Success!
        else:
            # Cleanup partial registration if any
            if success_p: user32.UnregisterHotKey(None, 1)
            if success_m: user32.UnregisterHotKey(None, 2)
            
            if attempt == 0:
                print("\n[!] Hotkeys busy. Attempting to close old instances...")
                kill_conflicting_instances()
                print("[i] Retrying registration...")
            else:
                print("\n[!] Error: Could not register hotkeys. They may be in use by another app.")
                return

    msg = wintypes.MSG()
    try:
        # Non-blocking message loop
        while True:
            if user32.PeekMessageA(ctypes.byref(msg), None, 0, 0, 1):
                if msg.message == 0x0012: # WM_QUIT
                    break
                if msg.message == 0x0312: # WM_HOTKEY
                    if msg.wParam == 1:
                        process_request()
                    elif msg.wParam == 2:
                        toggle_model()
                
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageA(ctypes.byref(msg))
            else:
                time.sleep(0.05)
            
    except KeyboardInterrupt:
        print("\n[!] Shutting down...")
    finally:
        user32.UnregisterHotKey(None, 1)
        user32.UnregisterHotKey(None, 2)

if __name__ == "__main__":
    main()
