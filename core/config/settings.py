import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Hotkey Mapping Constants ---
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008

VK_MAP = {
    # Arrows
    "UP": 0x26, "DOWN": 0x28, "LEFT": 0x25, "RIGHT": 0x27,
    # Navigation
    "PGUP": 0x21, "PGDN": 0x22, "PRIOR": 0x21, "NEXT": 0x22,
    "HOME": 0x24, "END": 0x23, "INSERT": 0x2D, "DELETE": 0x2E,
    # Symbols
    "PLUS": 0xBB, "MINUS": 0xBD, "EQUALS": 0xBB,
    "BACKSPACE": 0x08, "TAB": 0x09, "ENTER": 0x0D, "ESC": 0x1B, "SPACE": 0x20,
}

def parse_hotkey(env_var: str, default_str: str):
    """
    Parses a hotkey string like 'Ctrl+Alt+Shift+P' into (vk_code, modifiers).
    """
    raw = os.getenv(env_var, default_str)
    parts = raw.upper().split('+')
    
    modifiers = 0
    vk_code = 0
    
    for part in parts:
        part = part.strip()
        if part == "CTRL" or part == "CONTROL":
            modifiers |= MOD_CONTROL
        elif part == "ALT":
            modifiers |= MOD_ALT
        elif part == "SHIFT":
            modifiers |= MOD_SHIFT
        elif part == "WIN" or part == "WINDOWS":
            modifiers |= MOD_WIN
        elif part in VK_MAP:
            vk_code = VK_MAP[part]
        elif len(part) == 1:
            vk_code = ord(part)
        elif part.startswith("0X"):
            vk_code = int(part, 16)
            
    return vk_code, modifiers

# --- API Configuration ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SIDECAR_MONITOR_INDEX = int(os.getenv("SIDECAR_MONITOR_INDEX", 1))
PROJECT_ROOT = os.getenv("PROJECT_ROOT", os.getcwd())
TRANSCRIPTION_PATH = os.path.abspath(os.path.join(PROJECT_ROOT, os.getenv("TRANSCRIPTION_PATH", "transcription.txt")))

# --- Capture Configuration ---
CROP_MARGINS = {
    "top": int(os.getenv("SIDECAR_CROP_TOP", 120)),
    "bottom": int(os.getenv("SIDECAR_CROP_BOTTOM", 40)),
    "left": int(os.getenv("SIDECAR_CROP_LEFT", 0)),
    "right": int(os.getenv("SIDECAR_CROP_RIGHT", 0))
}

# --- Hotkey Configuration ---
HK_PIXEL = parse_hotkey("HOTKEY_PIXEL", "Ctrl+Alt+Shift+P")
HK_TALK = parse_hotkey("HOTKEY_TALK", "Ctrl+Alt+Shift+T")
HK_MODEL = parse_hotkey("HOTKEY_MODEL", "Ctrl+Alt+Shift+M")
HK_ENGINE = parse_hotkey("HOTKEY_ENGINE", "Ctrl+Alt+Shift+E")
HK_SKILL = parse_hotkey("HOTKEY_SKILL", "Ctrl+Alt+Shift+S")

HK_MOVE_UP = parse_hotkey("HOTKEY_MOVE_UP", "Ctrl+Alt+Up")
HK_MOVE_DOWN = parse_hotkey("HOTKEY_MOVE_DOWN", "Ctrl+Alt+Down")
HK_MOVE_LEFT = parse_hotkey("HOTKEY_MOVE_LEFT", "Ctrl+Alt+Left")
HK_MOVE_RIGHT = parse_hotkey("HOTKEY_MOVE_RIGHT", "Ctrl+Alt+Right")

HK_FONT_UP = parse_hotkey("HOTKEY_FONT_UP", "Ctrl+Alt+Plus")
HK_FONT_DOWN = parse_hotkey("HOTKEY_FONT_DOWN", "Ctrl+Alt+Minus")
HK_SCROLL_UP = parse_hotkey("HOTKEY_SCROLL_UP", "Ctrl+Alt+PgUp")
HK_SCROLL_DOWN = parse_hotkey("HOTKEY_SCROLL_DOWN", "Ctrl+Alt+PgDn")


# --- Intelligence Configuration ---
SIDECAR_ENGINE = os.getenv("SIDECAR_ENGINE", "gemini").lower()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_FLASH = os.getenv("MODEL_FLASH", "models/gemini-3-flash-preview")
MODEL_PRO = os.getenv("MODEL_PRO", "models/gemini-3-pro-preview")
GROQ_MODEL = os.getenv("GROQ_MODEL", "meta-llama/llama-4-maverick-17b-128e-instruct")
GROQ_STT_MODEL = os.getenv("GROQ_STT_MODEL", "whisper-large-v3-turbo")
THINKING_LEVEL = os.getenv("THINKING_LEVEL", "high")
AUDIO_SAMPLE_RATE = int(os.getenv("AUDIO_SAMPLE_RATE", 16000))

# --- Ghost Configuration ---
GHOST_MODE_AUTO = os.getenv("GHOST_MODE_AUTO", "False").lower() == "true"
GHOST_OPACITY = float(os.getenv("GHOST_OPACITY", 0.78))
GHOST_FONT_SIZE = int(os.getenv("GHOST_FONT_SIZE", 10))
GHOST_FONT_FAMILY = os.getenv("GHOST_FONT_FAMILY", "Consolas")

# --- Debug Configuration ---
SAVE_DEBUG_SNAPSHOTS = os.getenv("SIDECAR_DEBUG", "False").lower() == "true"
DEBUG_DIR = os.path.join(PROJECT_ROOT, "debug_snapshots")
