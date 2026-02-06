import sys
import signal
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from core.config import settings
from core.utils.session_manager import SessionManager
from core.ui.worker import SidecarWorker
from core.ui.hotkey_thread import HotkeyThread
from core.ui.terminal_ghost import TerminalGhostWindow
from core.utils.stdout_capture import StdoutCapture
from core.utils.logger import logger
from core.ui.cli import CLI

# Hotkey IDs
HK_ID_PIXEL = 101
HK_ID_TALK = 102
HK_ID_MODEL = 103
HK_ID_ENGINE = 104
HK_ID_SKILL = 105
HK_ID_FONT_INCREASE = 106  # Ctrl+Alt+=
HK_ID_FONT_DECREASE = 107  # Ctrl+Alt+-
HK_ID_MOVE_UP = 108     # Ctrl+Alt+Up
HK_ID_MOVE_DOWN = 109   # Ctrl+Alt+Down
HK_ID_MOVE_LEFT = 110   # Ctrl+Alt+Left
HK_ID_MOVE_RIGHT = 111  # Ctrl+Alt+Right
HK_ID_SCROLL_UP = 112   # Ctrl+Alt+PgUp
HK_ID_SCROLL_DOWN = 113 # Ctrl+Alt+PgDn


class SidecarApp:
    """
    Main application orchestrator for SidecarAI.
    Uses Terminal Ghost Mode for transparent, click-through console output.
    """
    
    def __init__(self):
        self.qt_app = QApplication.instance() or QApplication(sys.argv)
        self.session = SessionManager()
        
        # 1. Bootstrap components
        self.components = self.session.bootstrap()
        
        # 2. Initialize Terminal Ghost Window
        opacity = getattr(settings, 'GHOST_OPACITY', 0.78)
        font_size = getattr(settings, 'GHOST_FONT_SIZE', 10)
        font_family = getattr(settings, 'GHOST_FONT_FAMILY', "Consolas")
        
        self.terminal = TerminalGhostWindow(
            opacity=float(opacity),
            font_size=int(font_size),
            font_family=font_family
        )
        self.terminal.show()
        
        # 3. Capture stdout → Terminal
        self.stdout_capture = StdoutCapture(self.terminal.append_text)
        self.stdout_capture.start()
        logger.success("Terminal Ghost Mode ACTIVATED.")
        
        # 4. Initialize Worker
        self.worker = SidecarWorker(self.components)
        self.worker.start()

        # 5. Initialize Hotkeys
        MOD_CTRL_ALT = 0x0001 | 0x0002  # Ctrl+Alt (no Shift)
        
        self.hk_thread = HotkeyThread({
            settings.VK_P: (HK_ID_PIXEL, "Pixel [P]"),
            settings.VK_T: (HK_ID_TALK, "Talk [T]"),
            settings.VK_M: (HK_ID_MODEL, "Model [M]"),
            settings.VK_E: (HK_ID_ENGINE, "Engine [E]"),
            settings.VK_S: (HK_ID_SKILL, "Skill [S]"),
            # Font & Window controls (Ctrl+Alt)
            0xBB: (HK_ID_FONT_INCREASE, "Font+ [=]", MOD_CTRL_ALT),
            0xBD: (HK_ID_FONT_DECREASE, "Font- [-]", MOD_CTRL_ALT),
            0x26: (HK_ID_MOVE_UP, "Move Up", MOD_CTRL_ALT),
            0x28: (HK_ID_MOVE_DOWN, "Move Down", MOD_CTRL_ALT),
            0x25: (HK_ID_MOVE_LEFT, "Move Left", MOD_CTRL_ALT),
            0x27: (HK_ID_MOVE_RIGHT, "Move Right", MOD_CTRL_ALT),
            0x21: (HK_ID_SCROLL_UP, "Scroll Up", MOD_CTRL_ALT),
            0x22: (HK_ID_SCROLL_DOWN, "Scroll Down", MOD_CTRL_ALT),
        })
        self.hk_thread.signal_hotkey.connect(self._on_hotkey)
        self.hk_thread.start()

        # 6. Wire Signals
        self.worker.signal_chunk_update.connect(self._on_terminal_chunk)
        self.worker.signal_status_update.connect(self._on_status_update)
        
        # Track terminal state
        self._response_active = False
        self._inline_active = False

        # 7. Graceful Interrupt (Ctrl+C)
        signal.signal(signal.SIGINT, self._on_interrupt)
        self.interrupt_timer = QTimer()
        self.interrupt_timer.timeout.connect(lambda: None)
        self.interrupt_timer.start(500)

    def _on_interrupt(self, sig, frame):
        print()
        logger.warning("Interrupt received. Cleaning up...")
        self.qt_app.quit()

    def _on_terminal_chunk(self, chunk, vector):
        """Prints AI response chunks to the terminal."""
        if self._inline_active or not self._response_active:
            print()
            self._inline_active = False
            self._response_active = True
            
        color = CLI.Fore.CYAN if vector == "a" else CLI.Fore.GREEN
        print(f"{color}{chunk}{CLI.Style.RESET_ALL}", end="", flush=True)

    def _on_status_update(self, status):
        """Handle status updates from worker."""
        if "READY" in status:
            self._response_active = False
            self._inline_active = False
            CLI.print_ready()
        elif "Capturing" in status or "Analyzing" in status:
            if self._inline_active:
                print()
                self._inline_active = False
            logger.info(status)
        elif "RECORDING" in status:
            if self._inline_active:
                print()
                self._inline_active = False
            logger.info("Recording...")
        elif "Intent" in status:
            if self._inline_active:
                print()
                self._inline_active = False
            logger.info(f"Finalizing Intent: {status.split(':')[-1].strip()}")

    def _on_hotkey(self, hk_id):
        logger.debug(f"Hotkey triggered: ID={hk_id}")
        
        if hk_id == HK_ID_PIXEL:
            self.worker.handle_pixel_request()
        elif hk_id == HK_ID_TALK:
            self.worker.handle_verbal_request()
        elif hk_id == HK_ID_MODEL:
            self.worker.brain.toggle_model()
            logger.info(f"Model switched to {self.worker.brain.get_model_name()}")
            CLI.print_ready()
        elif hk_id == HK_ID_ENGINE:
            msg = self.worker.brain.switch_engine()
            logger.info(msg)
            CLI.print_ready()
        elif hk_id == HK_ID_FONT_INCREASE:
            self.terminal.increase_font_size()
        elif hk_id == HK_ID_FONT_DECREASE:
            self.terminal.decrease_font_size()
        elif hk_id == HK_ID_MOVE_UP:
            self.terminal.move_up(50)
        elif hk_id == HK_ID_MOVE_DOWN:
            self.terminal.move_down(50)
        elif hk_id == HK_ID_MOVE_LEFT:
            self.terminal.move_left(50)
        elif hk_id == HK_ID_MOVE_RIGHT:
            self.terminal.move_right(50)
        elif hk_id == HK_ID_SCROLL_UP:
            self.terminal.scroll_up(5)
        elif hk_id == HK_ID_SCROLL_DOWN:
            self.terminal.scroll_down(5)

    def run(self):
        exit_code = self.qt_app.exec()
        
        # Cleanup
        logger.info("Shutting down...")
        self.stdout_capture.stop()
        self.hk_thread.stop()
        self.worker.terminate()
        
        sys.exit(exit_code)


if __name__ == "__main__":
    is_debug = "--debug" in sys.argv
    
    if is_debug:
        import os
        os.environ["SIDECAR_DEBUG"] = "true"
        logger.update_level()
        
    try:
        app = SidecarApp()
        
        if is_debug:
            logger.info("Debug logging ENABLED.")
        
        app.run()
    except KeyboardInterrupt:
        print("\n")
        logger.warning("SidecarAI termination requested. Cleaning up...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal Startup Error: {e}")
        if is_debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)
