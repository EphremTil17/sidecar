import os
from dotenv import load_dotenv

def ensure_config():
    """
    Validates existence of .env and keys.
    If missing, prompts user and creates the file with comprehensive defaults.
    """
    env_path = ".env"
    template_path = ".env.template"
    
    # 1. Check existing .env
    if os.path.exists(env_path):
        load_dotenv(env_path, override=True)
        # We check for at least one valid key to consider setup "done", 
        # but the app might still error if the active engine key is missing.
        if (os.getenv("GOOGLE_API_KEY") and os.getenv("GOOGLE_API_KEY").startswith("AIza")) or \
           (os.getenv("GROQ_API_KEY") and os.getenv("GROQ_API_KEY").startswith("gsk_")):
            return True
    
    # 2. Setup Prompt
    print("\n" + "="*50)
    print("### SIDECAR AI: INITIAL SETUP ###")
    print("="*50)
    print("It looks like your configuration is missing or invalid.")
    print("Sidecar now supports dual engines: Gemini (Google) and Maverick (Groq).")
    
    print("\n[1] Enter Google API Key (Optional, for deep reasoning): ", end="")
    google_key = input().strip()
    
    print("[2] Enter Groq API Key (Optional, for instant speed): ", end="")
    groq_key = input().strip()
    
    if not google_key and not groq_key:
        print("[!] Error: You must provide at least one API key (Google or Groq).")
        return False
        
    # 3. Preferences
    default_engine = "gemini" if google_key else "groq"
    print(f"\n[i] Setting default engine to: {default_engine}")

    # 4. Generate .env content
    # If template exists, we try to be smart, otherwise use structured defaults
    env_lines = [
        "# --- Application Preferences ---",
        f"SIDECAR_ENGINE={default_engine}",
        "",
        "# --- API Configuration ---",
        f"GOOGLE_API_KEY={google_key}",
        f"GROQ_API_KEY={groq_key}",
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
        "GROQ_MODEL=meta-llama/llama-4-maverick-17b-128e-instruct",
        "SIDECAR_THINKING_LEVEL=high",
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
