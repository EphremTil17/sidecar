import sys
import signal
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, QObject, pyqtSignal
from core.config import settings
from core.utils.session_manager import SessionManager
from core.ui.worker import SidecarWorker
from core.ui.hotkey_thread import HotkeyThread
from core.ui.hotkey_orchestrator import HotkeyOrchestrator
from core.ui.terminal_ghost import TerminalGhostWindow
from core.utils.stdout_capture import StdoutCapture
from core.utils.events import bus, AppEvent
from core.utils.logger import logger
from core.ui.cli_feedback import CLIFeedbackHandler
from core.types.registry import ComponentRegistry

class SidecarApp(QObject):
    """
    Final Modular Orchestrator for SidecarAI.
    Coordinates specialized directors and UI components.
    """
    signal_append_text = pyqtSignal(str) # Thread-safe bridge for stdout

    def __init__(self, components: ComponentRegistry, manager: SessionManager, ghost_enabled: bool = False):
        super().__init__()
        
        self.qt_app = QApplication.instance()
        self.ghost_enabled = ghost_enabled
        self.session = manager
        self.components = components
        
        # 1. Terminal Ghost Overlay Setup
        self.terminal = self._init_ghost_window() if self.ghost_enabled else None
        
        # 2. Output & Feedback Layer
        self.stdout_capture = StdoutCapture(self.signal_append_text.emit)
        self.stdout_capture.start()
        
        self.feedback = CLIFeedbackHandler(self.stdout_capture, self.terminal)
        self.feedback.bind_timer(QTimer(self)) # Feed the ticker its timer

        # 3. Processing Layer (Worker)
        self.worker = SidecarWorker(self.components)
        self.worker.start()

        # 4. Hotkey Orchestration
        self.orchestrator = HotkeyOrchestrator(self.terminal)
        self.hk_thread = HotkeyThread(self.orchestrator.get_mappings())
        self.hk_thread.signal_hotkey.connect(self.orchestrator.dispatch)
        self.hk_thread.start()

        # 5. Global Event Routing
        bus.dispatch.connect(self._on_event)

        # 6. OS Interrupts (Ctrl+C Support)
        signal.signal(signal.SIGINT, lambda s, f: self.qt_app.quit())
        self.interrupt_timer = QTimer()
        self.interrupt_timer.timeout.connect(lambda: None) # Keep event loop alive for signals
        self.interrupt_timer.start(500)

    def _init_ghost_window(self):
        """Initializes and returns the transparent overlay window."""
        window = TerminalGhostWindow(
            bg_low=settings.GHOST_BG_ALPHA_LOW,
            bg_high=settings.GHOST_BG_ALPHA_HIGH,
            text_low=settings.GHOST_TEXT_ALPHA_LOW,
            text_high=settings.GHOST_TEXT_ALPHA_HIGH,
            font_size=settings.GHOST_FONT_SIZE,
            font_family=settings.GHOST_FONT_FAMILY,
            width=settings.GHOST_WIDTH,
            height=settings.GHOST_HEIGHT
        )
        geom = self.session._state.get("overlay_geometry")
        if geom:
            window.setGeometry(geom[0], geom[1], settings.GHOST_WIDTH, settings.GHOST_HEIGHT)
        
        window.show()
        logger.success("Terminal Ghost Mode ACTIVATED.")
        return window

    def _on_event(self, event, payload):
        """Central event router for the Sidecar ecosystem."""
        if event == AppEvent.AGENT_CHUNK_UPDATE:
            self.feedback.handle_chunk_update(payload)
            
        elif event == AppEvent.AGENT_STATUS_UPDATE:
            if "HANDSHAKE_START" in payload:
                self.feedback.start_ticker(payload.replace('HANDSHAKE_START:', ''))
                return
            
            # Prepare console for status log (newline injections, etc.)
            is_milestone = any(k in payload for k in ["Handshake with", "Thinking", "Awaiting"])
            self.feedback.prepare_for_status(is_milestone)
            
            # Delegate formatted printing to the feedback handler
            self.feedback.handle_status_update(payload)

    def run(self):
        """Starts the main event loop and handles final state persistence."""
        try:
            exit_code = self.qt_app.exec()
        finally:
            logger.info("Syncing session state...")
            geometry = None
            if self.terminal:
                geom = self.terminal.geometry()
                geometry = [geom.x(), geom.y(), geom.width(), geom.height()]
            
            self.session.commit(overlay_geometry=geometry)
            self.session.shutdown()
            sys.exit(exit_code)

if __name__ == "__main__":
    # CLI Flags
    if "--debug" in sys.argv:
        import os
        os.environ["SIDECAR_DEBUG"] = "true"
        logger.update_level()
    if "--verbose" in sys.argv:
        settings.VERBOSE_REASONING = True
        logger.info("Verbose Reasoning ENABLED.")
        
    qt_app = QApplication([sys.argv[0]])
    
    # Bootstrap
    manager = SessionManager()
    components = manager.bootstrap()
    
    app_logic = SidecarApp(components, manager, ghost_enabled="--ghost" in sys.argv)
    
    # Cleanup Chain
    manager.register_cleanup(app_logic.worker.stop)
    manager.register_cleanup(app_logic.hk_thread.stop)
    manager.register_cleanup(app_logic.stdout_capture.stop)
    manager.register_cleanup(components.recorder.stop)

    try:
        app_logic.run()
    except KeyboardInterrupt:
        print("\n")
        logger.warning("SidecarAI termination requested.")
        manager.shutdown()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal Startup Error: {e}")
        manager.shutdown()
        sys.exit(1)
