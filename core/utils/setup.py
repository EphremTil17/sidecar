import os
from dotenv import load_dotenv

def ensure_config():
    """
    Validates existence of .env and GOOGLE_API_KEY.
    If missing, prompts user and creates the file with comprehensive defaults.
    """
    env_path = ".env"
    template_path = ".env.template"
    
    # 1. Check existing .env
    if os.path.exists(env_path):
        load_dotenv(env_path, override=True)
        if os.getenv("GOOGLE_API_KEY") and os.getenv("GOOGLE_API_KEY").startswith("AIza"):
            return True
    
    # 2. Setup Prompt
    print("\n" + "="*50)
    print("### SIDECAR AI: INITIAL SETUP ###")
    print("="*50)
    print("It looks like your configuration is missing or invalid.")
    print("You can get a free API key at: https://aistudio.google.com/app/apikey")
    print("\nPlease enter your Google API Key (AIza...): ", end="")
    
    try:
        api_key = input().strip()
    except EOFError:
        return False
    
    if not api_key or not api_key.startswith("AIza"):
        print("[!] Error: Invalid or empty API Key format.")
        return False
        
    # 3. Handle Hotkeys and Margins (Optional prompts, using defaults)
    print("\n[i] Using default hotkeys: Ctrl+Alt+Shift + P (Process), M (Model), S (Swap)")
    print("[i] Using default crop margins: Top (120px), Bottom (40px)")
    print("[i] These can be changed anytime in the .env file.")

    # 4. Generate .env content
    # If template exists, we try to be smart, otherwise use structured defaults
    env_lines = [
        "# --- API Configuration ---",
        f"GOOGLE_API_KEY={api_key}",
        "",
        "# --- Screen Capture Configuration ---",
        "SIDECAR_MONITOR_INDEX=1",
        "SIDECAR_CROP_TOP=120",
        "SIDECAR_CROP_BOTTOM=40",
        "SIDECAR_CROP_LEFT=0",
        "SIDECAR_CROP_RIGHT=0",
        "",
        "# --- Hotkey Configuration ---",
        "HOTKEY_PROCESS=P",
        "HOTKEY_MODEL_TOGGLE=M",
        "HOTKEY_SKILL_SWAP=S",
        "",
        "# --- Intelligence Configuration ---",
        "MODEL_FLASH=models/gemini-3-flash-preview",
        "MODEL_PRO=models/gemini-3-pro-preview",
        "SIDECAR_THINKING_LEVEL=low",
        "",
        "# --- Debug Configuration ---",
        "SIDECAR_DEBUG=False"
    ]

    try:
        with open(env_path, "w", encoding="utf-8") as f:
            f.write("\n".join(env_lines) + "\n")
        
        print(f"\n[SUCCESS] Configuration saved to {env_path}")
        print("[i] Initializing session...")
        print("="*50 + "\n")
        
        # Reload immediately for current process
        load_dotenv(env_path, override=True)
        return True
    except Exception as e:
        print(f"[!] Critical Error writing .env: {e}")
        return False
