from core.config import settings
from core.utils.logger import logger

# Hotkey Unique Identifiers
HK_ID_PIXEL = 101
HK_ID_TALK = 102
HK_ID_MODEL = 103
HK_ID_ENGINE = 104
HK_ID_SKILL = 105
HK_ID_FONT_INCREASE = 106
HK_ID_FONT_DECREASE = 107
HK_ID_MOVE_UP = 108
HK_ID_MOVE_DOWN = 109
HK_ID_MOVE_LEFT = 110
HK_ID_MOVE_RIGHT = 111
HK_ID_SCROLL_UP = 112
HK_ID_SCROLL_DOWN = 113

class HotkeyOrchestrator:
    """
    Central dispatch for global hotkey events.
    
    This orchestrator acts as a bridge between the HotkeyManager and the 
    application's core functional layers (Worker, Terminal, Brain). 
    It ensures that hotkey registration and execution are decoupled 
    from the main application logic.
    """
    def __init__(self, worker, terminal=None):
        self.worker = worker
        self.terminal = terminal
        
    def get_mappings(self) -> dict:
        """
        Constructs the configuration mapping for the HotkeyThread.
        Maps VK codes from settings to internal Hotkey IDs and display labels.
        """
        return {
            settings.HK_PIXEL[0]: (HK_ID_PIXEL, "Pixel [P]", settings.HK_PIXEL[1]),
            settings.HK_TALK[0]: (HK_ID_TALK, "Talk [T]", settings.HK_TALK[1]),
            settings.HK_MODEL[0]: (HK_ID_MODEL, "Model [M]", settings.HK_MODEL[1]),
            settings.HK_ENGINE[0]: (HK_ID_ENGINE, "Engine [E]", settings.HK_ENGINE[1]),
            settings.HK_SKILL[0]: (HK_ID_SKILL, "Skill [S]", settings.HK_SKILL[1]),
            
            # Spatial Controls
            settings.HK_MOVE_UP[0]: (HK_ID_MOVE_UP, "Move Up", settings.HK_MOVE_UP[1]),
            settings.HK_MOVE_DOWN[0]: (HK_ID_MOVE_DOWN, "Move Down", settings.HK_MOVE_DOWN[1]),
            settings.HK_MOVE_LEFT[0]: (HK_ID_MOVE_LEFT, "Move Left", settings.HK_MOVE_LEFT[1]),
            settings.HK_MOVE_RIGHT[0]: (HK_ID_MOVE_RIGHT, "Move Right", settings.HK_MOVE_RIGHT[1]),
            
            # Appearance & Navigation
            settings.HK_FONT_UP[0]: (HK_ID_FONT_INCREASE, "Font+", settings.HK_FONT_UP[1]),
            settings.HK_FONT_DOWN[0]: (HK_ID_FONT_DECREASE, "Font-", settings.HK_FONT_DOWN[1]),
            settings.HK_SCROLL_UP[0]: (HK_ID_SCROLL_UP, "Scroll Up", settings.HK_SCROLL_UP[1]),
            settings.HK_SCROLL_DOWN[0]: (HK_ID_SCROLL_DOWN, "Scroll Down", settings.HK_SCROLL_DOWN[1]),
        }

    def dispatch(self, hk_id: int):
        """Dispatched from the UI thread to trigger safe cross-thread actions."""
        logger.debug(f"Hotkey event: {hk_id}")
        
        # 1. Primary AI Analysis Vectors
        if hk_id == HK_ID_PIXEL:
            self.worker.handle_pixel_request()
            return
        elif hk_id == HK_ID_TALK:
            self.worker.handle_verbal_request()
            return
            
        # 2. Intelligence State Management
        elif hk_id == HK_ID_MODEL:
            self.worker.brain.toggle_model()
            logger.info(f"Active model: {self.worker.brain.get_model_name()}")
            return
        elif hk_id == HK_ID_ENGINE:
            msg = self.worker.brain.switch_engine()
            logger.info(msg)
            return
            
        # UI-dependent hotkeys (only dispatch if terminal exists)
        if not self.terminal:
            return

        # 3. Dynamic UI Transformation
        if hk_id == HK_ID_FONT_INCREASE:
            self.terminal.increase_font_size()
        elif hk_id == HK_ID_FONT_DECREASE:
            self.terminal.decrease_font_size()
            
        # 4. Terminal Placement
        elif hk_id == HK_ID_MOVE_UP:
            self.terminal.move_up(50)
        elif hk_id == HK_ID_MOVE_DOWN:
            self.terminal.move_down(50)
        elif hk_id == HK_ID_MOVE_LEFT:
            self.terminal.move_left(50)
        elif hk_id == HK_ID_MOVE_RIGHT:
            self.terminal.move_right(50)
            
        # 5. Terminal History Navigation
        elif hk_id == HK_ID_SCROLL_UP:
            self.terminal.scroll_up(5)
        elif hk_id == HK_ID_SCROLL_DOWN:
            self.terminal.scroll_down(5)
