import os
from dotenv import load_dotenv

def ensure_config():
    """
    Validates existence of the environment configuration and API keys.
    If missing, initiates an interactive setup and generates a healthy .env file.
    """
    env_path = ".env"
    
    # 1. Immediate validation of existing configuration
    if os.path.exists(env_path):
        load_dotenv(env_path, override=True)
        # We allow either a Google or Groq key to proceed.
        # Strict prefix checks (e.g., 'AIza') were removed to support varying key formats.
        if os.getenv("GOOGLE_API_KEY") or os.getenv("GROQ_API_KEY"):
            return True
    
    # 2. Interactive Setup Wizard
    print("\n" + "="*50)
    print("### SIDECAR AI: INITIAL SETUP ###")
    print("="*50)
    print("Configuration missing or invalid. Let's initialize your environment.")
    print("Sidecar supports dual engines: Gemini (Google) and Maverick (Groq).")
    
    print("\n[1] Enter Google API Key (Optional, for deep reasoning): ", end="")
    google_key = input().strip()
    
    print("[2] Enter Groq API Key (Optional, for instant speed): ", end="")
    groq_key = input().strip()
    
    if not google_key and not groq_key:
        print("[!] Error: You must provide at least one API key.")
        return False
        
    # 3. Derive Intelligent Defaults
    default_engine = "gemini" if google_key else "groq"
    
    # 4. Environment Template Construction
    # We use a clean, structured set of defaults to ensure the app boots successfully.
    env_content = f"""# --- Application Identification ---
SIDECAR_ENGINE={default_engine}

# --- API Configuration ---
GOOGLE_API_KEY={google_key}
GROQ_API_KEY={groq_key}

# --- Screen Capture Configuration ---
# Standard 16:9 monitor safe-zones
SIDECAR_MONITOR_INDEX=1
SIDECAR_CROP_TOP=120
SIDECAR_CROP_BOTTOM=40
SIDECAR_CROP_LEFT=0
SIDECAR_CROP_RIGHT=0

# --- Hotkey Configuration (VK Codes) ---
# Primary interface hotkeys
HOTKEY_PROCESS=P
HOTKEY_MODEL_TOGGLE=M
HOTKEY_SKILL_SWAP=S

# --- Intelligence Model Configuration ---
MODEL_FLASH=models/gemini-3-flash-preview
MODEL_PRO=models/gemini-3-pro-preview
GROQ_MODEL=meta-llama/llama-4-maverick-17b-128e-instruct

# --- Visual Preferences ---
GHOST_OPACITY=0.78
GHOST_FONT_SIZE=10
GHOST_FONT_FAMILY=Consolas

# --- Troubleshooting ---
SIDECAR_DEBUG=False
"""

    try:
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(env_content.strip() + "\n")
        
        print(f"\n[SUCCESS] Environment serialized to {env_path}")
        print("[i] Rebooting with persistent session...")
        print("="*50 + "\n")
        
        # Load the newly created environment for immediate use
        load_dotenv(env_path, override=True)
        return True
    except Exception as e:
        print(f"[!] File System Error: Unable to write .env: {e}")
        return False
