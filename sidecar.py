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
from core.ui.cli import CLI
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
        
        # 2. UI Layer (Optional Ghost Terminal)
        self.terminal = None
        if self.ghost_enabled:
            self.terminal = TerminalGhostWindow(
                bg_low=settings.GHOST_BG_ALPHA_LOW,
                bg_high=settings.GHOST_BG_ALPHA_HIGH,
                text_low=settings.GHOST_TEXT_ALPHA_LOW,
                text_high=settings.GHOST_TEXT_ALPHA_HIGH,
                font_size=settings.GHOST_FONT_SIZE,
                font_family=settings.GHOST_FONT_FAMILY,
                width=settings.GHOST_WIDTH,
                height=settings.GHOST_HEIGHT
            )
            
            # Restore previous window geometry if cached
            geom = self.session._state.get("overlay_geometry")
            if geom:
                # Use cached position (x, y) but prioritize .env for dimensions (w, h)
                self.terminal.setGeometry(geom[0], geom[1], settings.GHOST_WIDTH, settings.GHOST_HEIGHT)
            
            self.terminal.show()
            # Note: We do NOT connect signal_append_text to the terminal.
            # Mirroring the console into the overlay causes 'ANSI Garbage' and duplicate streams.
            # The overlay is exclusively for AI Markdown and clean HUD events.
            logger.success("Terminal Ghost Mode ACTIVATED.")
        else:
            logger.info("Running in standard Terminal Mode.")
        
        # 3. Output Redirection (via Signal Bridge)
        # Even if the ghost terminal is off, we still start capture 
        # to ensure the signal is managed correctly, though it will
        # just print to the standard console via the capture's fast-path.
        self.stdout_capture = StdoutCapture(self.signal_append_text.emit)
        self.stdout_capture.start()
        
        # 4. Processing Layer (Worker)
        # Background worker handles AI analysis to keep the main UI responsive.
        self.worker = SidecarWorker(self.components)
        self.worker.start()

        # 5. Hotkey Orchestration (Modular)
        # Centralizes hotkey logic and keeps it separated from core business logic.
        self.orchestrator = HotkeyOrchestrator(self.terminal)
        self.hk_thread = HotkeyThread(self.orchestrator.get_mappings())
        self.hk_thread.signal_hotkey.connect(self.orchestrator.dispatch)
        self.hk_thread.start()

        # 6. Lifecycle Monitoring
        # Note: All AI-to-UI communication now flows through the AppEventBus
        # for maximum decoupling and observability.
        bus.dispatch.connect(self._on_event)
        
        self._response_active = False
        self._inline_active = False

        # 7. OS Interrupts (Ensures Ctrl+C works in the console)
        signal.signal(signal.SIGINT, lambda s, f: self.qt_app.quit())
        self.interrupt_timer = QTimer()
        self.interrupt_timer.timeout.connect(lambda: None)
        self.interrupt_timer.start(500)

    def _on_event(self, event, payload):
        """Central event dispatcher for the main orchestrator."""
        if event == AppEvent.AGENT_CHUNK_UPDATE:
            # ONLY print to terminal if the Ghost Overlay is NOT active
            if not self.terminal:
                chunk, vector = payload
                self._on_terminal_chunk(chunk, vector)
        elif event == AppEvent.AGENT_STATUS_UPDATE:
            # ONLY print status to CLI if Ghost Overlay is NOT active
            if not self.terminal:
                self._on_status_update(payload)

    def _on_terminal_chunk(self, chunk, vector):
        """Visualizer for AI streaming chunks in the CLI console."""
        # 1. Update the console via ANSI path (SILENCED capture to prevent duplicates)
        self.stdout_capture.set_muted(True)
        try:
            color = CLI.Fore.CYAN if vector == "a" else CLI.Fore.GREEN
            print(f"{color}{chunk}{CLI.Style.RESET_ALL}", end="", flush=True)
        finally:
            self.stdout_capture.set_muted(False)

    def _on_status_update(self, status):
        """Unified status listener for CLI feedback."""
        if "READY" in status:
            self._response_active = False
            self._inline_active = False
            CLI.print_ready()
        elif any(k in status for k in ["Capturing", "Analyzing", "RECORDING", "Intent", "Latency"]):
            if self._inline_active:
                print()
                self._inline_active = False
            
            if "Intent" in status:
                logger.info(f"Finalizing Intent: {status.split(':')[-1].strip()}")
            elif "RECORDING" in status:
                logger.info("Recording...")
            else:
                logger.info(status)

    def run(self):
        """Starts the main event loop."""
        try:
            exit_code = self.qt_app.exec()
        finally:
            # Lifecycle Persistence & Cleanup
            logger.info("Syncing session state...")
            geometry = None
            if self.terminal:
                geom = self.terminal.geometry()
                geometry = [geom.x(), geom.y(), geom.width(), geom.height()]
            
            self.session.commit(overlay_geometry=geometry)
            self.session.shutdown()
            sys.exit(exit_code)

if __name__ == "__main__":
    if "--debug" in sys.argv:
        import os
        os.environ["SIDECAR_DEBUG"] = "true"
        logger.update_level()
        
    if "--verbose" in sys.argv:
        settings.VERBOSE_REASONING = True
        logger.info("Verbose Reasoning ENABLED.")
        
    # Create standard Qt App instance FIRST
    qt_app = QApplication([sys.argv[0]])
    
    # 1. Logic & State Setup
    manager = SessionManager()
    components = manager.bootstrap()
    ghost_mode = "--ghost" in sys.argv
    
    app_logic = SidecarApp(components, manager, ghost_enabled=ghost_mode)
    
    # 2. Cleanup Registration (Ensures threads stop on Ctrl+C)
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
