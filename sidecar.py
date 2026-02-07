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
from core.utils.logger import logger
from core.ui.cli import CLI

class SidecarApp(QObject):
    """
    Final Modular Orchestrator for SidecarAI.
    Coordinates specialized directors and UI components.
    """
    signal_append_text = pyqtSignal(str) # Thread-safe bridge for stdout

    def __init__(self):
        super().__init__()
        
        # Shield Qt from custom CLI flags like --debug or --ghost
        # This prevents QApplication from complaining about unknown command line arguments.
        self.qt_app = QApplication.instance() or QApplication([sys.argv[0]])
        
        # Check for Ghost Mode activation
        self.ghost_enabled = "--ghost" in sys.argv
        
        self.session = SessionManager()
        
        # 1. Bootstrap components (Engines, Directors, etc.)
        self.components = self.session.bootstrap()
        
        # 2. UI Layer (Optional Ghost Terminal)
        self.terminal = None
        if self.ghost_enabled:
            self.terminal = TerminalGhostWindow(
                opacity=settings.GHOST_OPACITY,
                font_size=settings.GHOST_FONT_SIZE,
                font_family=settings.GHOST_FONT_FAMILY
            )
            self.terminal.show()
            # Connect signal to UI slot only if active
            self.signal_append_text.connect(self.terminal.append_text)
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
        self.orchestrator = HotkeyOrchestrator(self.worker, self.terminal)
        self.hk_thread = HotkeyThread(self.orchestrator.get_mappings())
        self.hk_thread.signal_hotkey.connect(self.orchestrator.dispatch)
        self.hk_thread.start()

        # 6. Lifecycle Monitoring
        self.worker.signal_chunk_update.connect(self._on_terminal_chunk)
        self.worker.signal_status_update.connect(self._on_status_update)
        
        self._response_active = False
        self._inline_active = False

        # 7. OS Interrupts (Ensures Ctrl+C works in the console)
        signal.signal(signal.SIGINT, lambda s, f: self.qt_app.quit())
        self.interrupt_timer = QTimer()
        self.interrupt_timer.timeout.connect(lambda: None)
        self.interrupt_timer.start(500)

    def _on_terminal_chunk(self, chunk, vector):
        """Visualizer for AI streaming chunks in the CLI console."""
        if self._inline_active or not self._response_active:
            print()
            self._inline_active = False
            self._response_active = True
        color = CLI.Fore.CYAN if vector == "a" else CLI.Fore.GREEN
        print(f"{color}{chunk}{CLI.Style.RESET_ALL}", end="", flush=True)

    def _on_status_update(self, status):
        """Unified status listener for CLI feedback."""
        if "READY" in status:
            self._response_active = False
            self._inline_active = False
            CLI.print_ready()
        elif any(k in status for k in ["Capturing", "Analyzing", "RECORDING", "Intent"]):
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
        exit_code = self.qt_app.exec()
        logger.info("Shutting down...")
        self.stdout_capture.stop()
        self.hk_thread.stop()
        self.worker.terminate()
        sys.exit(exit_code)

if __name__ == "__main__":
    if "--debug" in sys.argv:
        import os
        os.environ["SIDECAR_DEBUG"] = "true"
        logger.update_level()
        
    try:
        SidecarApp().run()
    except KeyboardInterrupt:
        print("\n")
        logger.warning("SidecarAI termination requested.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal Startup Error: {e}")
        sys.exit(1)
