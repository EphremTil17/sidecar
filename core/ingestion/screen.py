import os
import io
import mss
import mss.tools
import numpy as np
from datetime import datetime
from PIL import Image
from core.config import settings
from core.utils import monitor_utils

class ScreenCapture:
    def __init__(self, monitor_index=None):
        self.monitor_index = monitor_index

    def set_monitor(self, index):
        self.monitor_index = index

    def capture(self):
        """
        High-Performance Capture Pipeline (Sidecar 3.0):
        Uses Zero-Copy NumPy buffers to minimize memory allocations.
        """
        if self.monitor_index is None:
            return None

        try:
            with mss.mss() as sct:
                try:
                    mon = sct.monitors[self.monitor_index]
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
                
                # 1. Grab raw pixels as memoryview
                # MSS grab() is fast, but we immediately cast to NumPy to avoid copies.
                sct_img = sct.grab(bbox)
                
                # Convert raw BGRA to NumPy RGB (dropping Alpha for AI analysis)
                # This is a very fast view-based slice in NumPy.
                frame = np.array(sct_img, dtype=np.uint8)
                img_rgb = frame[:, :, 2::-1] # BGRA -> RGB
            
            # 2. Fast Scaling (Downsize to 1280px max)
            MAX_DIM = 1280
            h, w = img_rgb.shape[:2]
            
            if w > MAX_DIM or h > MAX_DIM:
                scale = MAX_DIM / max(w, h)
                new_w, new_h = int(w * scale), int(h * scale)
                
                # Use PIL only for the final resize-to-save step as it's highly optimized
                # for downsizing with BILINEAR/BICUBIC filters.
                img = Image.fromarray(img_rgb)
                img = img.resize((new_w, new_h), Image.Resampling.BILINEAR)
            else:
                img = Image.fromarray(img_rgb)
            
            # 3. Fast PNG compression
            img_buffer = io.BytesIO()
            img.save(img_buffer, format="PNG", optimize=False, compress_level=1)
            png_bytes = img_buffer.getvalue()

            # DEBUG: Save snapshot if enabled
            if settings.SAVE_DEBUG_SNAPSHOTS:
                self._save_debug_snapshot(png_bytes)

            return png_bytes
            
        except Exception as e:
            from core.utils.logger import logger
            logger.error(f"Screen capture failed: {e}")
            return None

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
    try:
        available = get_available_monitors()
    except Exception:
        available = []

    # 1. Check Env Var via Settings
    if settings.SIDECAR_MONITOR_INDEX:
        try:
            idx = int(settings.SIDECAR_MONITOR_INDEX)
            for mon in available:
                try:
                    if mon.get('index') == idx:
                        return idx
                except (KeyError, TypeError):
                    continue
        except (ValueError, TypeError):
            pass

    # 2. Return Primary
    for mon in available:
        try:
            if mon.get('primary'):
                return mon.get('index', 1)
        except (KeyError, TypeError):
            continue

    return 1 # Fallback
