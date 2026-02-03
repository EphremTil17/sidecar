import ctypes
from ctypes import wintypes
import time

# Constants
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
WM_QUIT = 0x0012
WM_HOTKEY = 0x0312

class HotkeyManager:
    def __init__(self):
        self.user32 = ctypes.windll.user32
        self.hotkeys = {}

    def register_hotkey(self, id, vk_code, callback):
        """
        Registers a global hotkey with configured modifiers.
        Returns True if successful.
        """
        from core.config import settings
        modifiers = settings.MODIFIERS
        success = self.user32.RegisterHotKey(None, id, modifiers, vk_code)
        if success:
            self.hotkeys[id] = callback
        return success

    def unregister_all(self):
        for id in self.hotkeys:
            self.user32.UnregisterHotKey(None, id)
        self.hotkeys.clear()

    def listen(self, exit_callback=None):
        """
        Starts the message loop. 
        Blocking call until WM_QUIT is received or interrupted.
        """
        msg = wintypes.MSG()
        try:
            while True:
                if self.user32.PeekMessageA(ctypes.byref(msg), None, 0, 0, 1):
                    if msg.message == WM_QUIT:
                        break
                    
                    if msg.message == WM_HOTKEY:
                        id = msg.wParam
                        if id in self.hotkeys:
                            self.hotkeys[id]()
                    
                    self.user32.TranslateMessage(ctypes.byref(msg))
                    self.user32.DispatchMessageA(ctypes.byref(msg))
                else:
                    time.sleep(0.05)
        except KeyboardInterrupt:
            if exit_callback:
                exit_callback()
        finally:
            self.unregister_all()
