import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_vk_code(char, default):
    """Simple helper to convert a character string to a Windows Virtual Key code."""
    val = os.getenv(char)
    if not val:
        return default
    
    # If it's a single character like 'P', convert to 0x50
    if len(val) == 1:
        return ord(val.upper())
    
    # If it's already a hex string like 0x50
    if val.startswith('0x'):
        return int(val, 16)
    
    return default

# API Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SIDECAR_MONITOR_INDEX = os.getenv("SIDECAR_MONITOR_INDEX")

# Capture Configuration
CROP_MARGINS = {
    "top": int(os.getenv("SIDECAR_CROP_TOP", 120)),
    "bottom": int(os.getenv("SIDECAR_CROP_BOTTOM", 40)),
    "left": int(os.getenv("SIDECAR_CROP_LEFT", 0)),
    "right": int(os.getenv("SIDECAR_CROP_RIGHT", 0))
}

# Hotkey Configuration (Virtual Key Codes)
# Default Modifiers: Ctrl (0x0002) + Alt (0x0001) + Shift (0x0004) = 0x0007
MODIFIERS = 0x0001 | 0x0002 | 0x0004 
VK_P = get_vk_code("HOTKEY_PROCESS", 0x50)        # Default 'P'
VK_M = get_vk_code("HOTKEY_MODEL_TOGGLE", 0x4D) # Default 'M'
VK_S = get_vk_code("HOTKEY_SKILL_SWAP", 0x53)    # Default 'S'
VK_E = 0x45                                    # 'E' for Engine Toggle

# Intelligence Configuration
SIDECAR_ENGINE = os.getenv("SIDECAR_ENGINE", "gemini").lower()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

MODEL_FLASH = os.getenv("MODEL_FLASH", "models/gemini-3-flash-preview")
MODEL_PRO = os.getenv("MODEL_PRO", "models/gemini-3-pro-preview")
GROQ_MODEL = os.getenv("GROQ_MODEL", "meta-llama/llama-4-maverick-17b-128e-instruct")
THINKING_LEVEL = os.getenv("SIDECAR_THINKING_LEVEL", "high") # Options: low, medium, high

# State Defaults
DEFAULT_MONITOR_INDEX = 1

# Debug Configuration
DEBUG_DIR = "debug_output"
SAVE_DEBUG_SNAPSHOTS = os.getenv("SIDECAR_DEBUG", "False").lower() == "true"
