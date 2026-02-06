from PyQt6.QtCore import QThread, pyqtSignal
from core.drivers.hotkeys import HotkeyManager
from core.utils.logger import logger

class HotkeyThread(QThread):
    """
    Wraps HotkeyManager in a QThread to prevent blocking the GUI.
    Emits signals when hotkeys are pressed.
    """
    signal_hotkey = pyqtSignal(int) # Emits the hotkey ID

    def __init__(self, mappings: dict):
        super().__init__()
        self.manager = HotkeyManager()
        # Mappings format: {VK_CODE: (id, label)} or {VK_CODE: (id, label, modifiers)}
        self.mappings = mappings

    def run(self):
        logger.info("Hotkey Thread started.")
        for vk, mapping in self.mappings.items():
            if len(mapping) == 3:
                hk_id, label, modifiers = mapping
            else:
                hk_id, label = mapping
                modifiers = None  # Use default from HotkeyManager
                
            if self.manager.register_hotkey(hk_id, vk, lambda id=hk_id: self.signal_hotkey.emit(id), modifiers):
                logger.debug(f"Registered hotkey: {label} (ID: {hk_id})")
            else:
                logger.error(f"Failed to register hotkey: {label}")

        self.manager.listen(exit_callback=lambda: logger.warning("Hotkey thread shutting down."))

    def stop(self):
        self.manager.unregister_all()
        self.terminate()
        self.wait()
