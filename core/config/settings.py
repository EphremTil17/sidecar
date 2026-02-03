import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SIDECAR_MONITOR_INDEX = os.getenv("SIDECAR_MONITOR_INDEX")

# Capture Configuration
CROP_MARGINS = {"top": 120, "bottom": 40, "left": 0, "right": 0}

# Hotkey Configuration (Virtual Key Codes)
VK_P = 0x50 # 'P' for Process
VK_M = 0x4D # 'M' for Model Toggle
VK_S = 0x53 # 'S' for Skill Swap

# State Defaults
DEFAULT_MONITOR_INDEX = 1

# Debug Configuration
DEBUG_DIR = "debug_output"
SAVE_DEBUG_SNAPSHOTS = os.getenv("SIDECAR_DEBUG", "False").lower() == "true"
