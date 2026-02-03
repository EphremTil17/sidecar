import os
import mss
import mss.tools
from datetime import datetime
from core.config import settings
from core.utils import monitor_utils

class ScreenCapture:
    def __init__(self, monitor_index=None):
        self.monitor_index = monitor_index
        self.sct = mss.mss()

    def set_monitor(self, index):
        self.monitor_index = index

    def capture(self):
        """Captures the configured monitor and crops it, returning raw PNG bytes."""
        if self.monitor_index is None:
            return None

        try:
            mon = self.sct.monitors[self.monitor_index]
        except IndexError:
            return None

        # Calculate crop geometry
        margins = settings.CROP_MARGINS
        bbox = {
            "top": mon["top"] + margins["top"],
            "left": mon["left"] + margins["left"],
            "width": mon["width"] - margins["left"] - margins["right"],
            "height": mon["height"] - margins["top"] - margins["bottom"],
            "mon": self.monitor_index
        }
        
        # Grab the data
        sct_img = self.sct.grab(bbox)
        
        # Convert to PNG bytes
        png_bytes = mss.tools.to_png(sct_img.rgb, sct_img.size)

        # DEBUG: Save snapshot if enabled
        if settings.SAVE_DEBUG_SNAPSHOTS:
            self._save_debug_snapshot(png_bytes)

        return png_bytes

    def _save_debug_snapshot(self, png_bytes):
        """Saves the capture to the debug directory for visual verification."""
        if not os.path.exists(settings.DEBUG_DIR):
            os.makedirs(settings.DEBUG_DIR)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"capture_{timestamp}.png"
        filepath = os.path.join(settings.DEBUG_DIR, filename)
        
        try:
            with open(filepath, "wb") as f:
                f.write(png_bytes)
            print(f"[debug] Snapshot saved to: {filepath}")
        except Exception as e:
            print(f"[!] Warning: Failed to save debug snapshot: {e}")

def get_available_monitors():
    """Returns a list of available monitors."""
    return monitor_utils.list_monitors()

def get_default_monitor_index():
    """Returns the primary monitor index or the one set in settings."""
    available = get_available_monitors()
    
    # 1. Check Env Var via Settings
    if settings.SIDECAR_MONITOR_INDEX:
        try:
            idx = int(settings.SIDECAR_MONITOR_INDEX)
            for mon in available:
                if mon['index'] == idx:
                    return idx
        except ValueError:
            pass

    # 2. Return Primary
    for mon in available:
        if mon['primary']:
            return mon['index']
    
    return 1 # Fallback
