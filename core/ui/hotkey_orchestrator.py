from core.config import settings
from core.utils.events import AppEvent, bus
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
HK_ID_HIDE_TEXT = 114
HK_ID_INGEST = 115


class HotkeyOrchestrator:
    """
    Central dispatch for global hotkey events.

    This orchestrator acts as a bridge between the HotkeyManager and the
    application's core functional layers (Worker, Terminal, Brain).
    It ensures that hotkey registration and execution are decoupled
    from the main application logic.
    """

    def __init__(self, terminal=None):
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
            settings.HK_MOVE_DOWN[0]: (
                HK_ID_MOVE_DOWN,
                "Move Down",
                settings.HK_MOVE_DOWN[1],
            ),
            settings.HK_MOVE_LEFT[0]: (
                HK_ID_MOVE_LEFT,
                "Move Left",
                settings.HK_MOVE_LEFT[1],
            ),
            settings.HK_MOVE_RIGHT[0]: (
                HK_ID_MOVE_RIGHT,
                "Move Right",
                settings.HK_MOVE_RIGHT[1],
            ),
            # Appearance & Navigation
            settings.HK_FONT_UP[0]: (
                HK_ID_FONT_INCREASE,
                "Font+",
                settings.HK_FONT_UP[1],
            ),
            settings.HK_FONT_DOWN[0]: (
                HK_ID_FONT_DECREASE,
                "Font-",
                settings.HK_FONT_DOWN[1],
            ),
            settings.HK_SCROLL_UP[0]: (
                HK_ID_SCROLL_UP,
                "Scroll Up",
                settings.HK_SCROLL_UP[1],
            ),
            settings.HK_SCROLL_DOWN[0]: (
                HK_ID_SCROLL_DOWN,
                "Scroll Down",
                settings.HK_SCROLL_DOWN[1],
            ),
            settings.HK_HIDE_TEXT[0]: (
                HK_ID_HIDE_TEXT,
                "Focus Mode",
                settings.HK_HIDE_TEXT[1],
            ),
            settings.HK_INGEST[0]: (HK_ID_INGEST, "Ingest [I]", settings.HK_INGEST[1]),
        }

    def dispatch(self, hk_id: int):
        """Dispatched from the UI thread to trigger safe cross-thread actions."""

        # 1. Direct Mappings (Simple Event Triggers)
        event_map = {
            HK_ID_PIXEL: AppEvent.TRIGGER_PIXEL,
            HK_ID_TALK: AppEvent.TRIGGER_TALK,
            HK_ID_INGEST: AppEvent.TRIGGER_INGEST,
            HK_ID_MODEL: AppEvent.INTELLIGENCE_TOGGLE_MODEL,
            HK_ID_ENGINE: AppEvent.INTELLIGENCE_SWITCH_ENGINE,
            HK_ID_SKILL: AppEvent.INTELLIGENCE_SWITCH_SKILL,
            HK_ID_HIDE_TEXT: AppEvent.UI_FOCUS_TOGGLE,
        }

        if hk_id in event_map:
            logger.debug(f"Hotkey event: {event_map[hk_id].name} ({hk_id})")
            bus.publish(event_map[hk_id])
            return

        # 2. Parameterized Mappings
        self._dispatch_parameterized(hk_id)

    def _dispatch_parameterized(self, hk_id: int):
        """Handles hotkeys that require additional metadata."""
        if hk_id == HK_ID_FONT_INCREASE:
            bus.publish(AppEvent.UI_FONT_SCALE, 1)
        elif hk_id == HK_ID_FONT_DECREASE:
            bus.publish(AppEvent.UI_FONT_SCALE, -1)
        elif hk_id == HK_ID_MOVE_UP:
            bus.publish(AppEvent.UI_MOVE, (0, -50))
        elif hk_id == HK_ID_MOVE_DOWN:
            bus.publish(AppEvent.UI_MOVE, (0, 50))
        elif hk_id == HK_ID_MOVE_LEFT:
            bus.publish(AppEvent.UI_MOVE, (-50, 0))
        elif hk_id == HK_ID_MOVE_RIGHT:
            bus.publish(AppEvent.UI_MOVE, (50, 0))
        elif hk_id == HK_ID_SCROLL_UP:
            bus.publish(AppEvent.UI_SCROLL, -5)
        elif hk_id == HK_ID_SCROLL_DOWN:
            bus.publish(AppEvent.UI_SCROLL, 5)
