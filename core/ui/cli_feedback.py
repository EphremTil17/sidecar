import sys
import time

from core.ui.cli import CLI
from core.utils.logger import logger


class CLIFeedbackHandler:
    """
    Dedicated handler for CLI-side feedback, tickers, and status formatting.
    Decouples the UI presentation from the main Sidecar orchestrator.
    """

    def __init__(self, stdout_capture, terminal_overlay=None):
        self.stdout_capture = stdout_capture
        self.terminal = terminal_overlay  # Ghost Overlay (if active)

        # Ticker State
        self._ticker_timer = None
        self._turn_start_time = 0
        self._ticker_model = ""
        self._ticker_dots = 0
        self._is_thinking = False
        self._needs_newline = False
        self._last_completion_msg = None

    def bind_timer(self, timer):
        """Binds a QTimer for the ticker updates."""
        self._ticker_timer = timer
        self._ticker_timer.timeout.connect(self._update_ticker)

    def handle_status_update(self, status):
        """Unified status listener for CLI feedback."""
        if "READY" in status:
            self._handle_ready_status(status)
            return

        if status.startswith("HANDSHAKE_START:"):
            # Start ticker but DON'T log yet to avoid double entries
            model_name = status.split(":", 1)[1].strip()
            self.start_ticker(model_name)
            return

        if "Thinking" in status:
            self._is_thinking = True
            return

        self._process_milestone_status(status)

    def _handle_ready_status(self, status):
        """Handle systems-ready signal."""
        # Aesthetic Cleanup: Ensure the ticker from the previous turn is gone
        if self._ticker_timer and self._ticker_timer.isActive():
            self.stop_ticker()

        # Phase 1: Close the previous turn visually
        buffered_msg = self._last_completion_msg
        self._last_completion_msg = None

        # Phase 2: Print the ready bar
        CLI.print_ready(pre_status=buffered_msg)

    def _process_milestone_status(self, status):
        """Process standard operational milestones."""
        milestones = [
            "Capturing",
            "Analyzing",
            "RECORDING",
            "Intent",
            "Offloaded",
            "Response Streaming",
            "Complete",
        ]
        if any(k in status for k in milestones):
            if "Intent" in status:
                logger.info(f"Finalizing Intent: {status.split(':')[-1].strip()}")
            elif "RECORDING" in status:
                logger.debug("Hot Vector (Voice) initialized.")
            elif any(k in status for k in ["Offloaded", "Response Streaming", "Complete"]):
                self._handle_completion_milestones(status)
            else:
                self._safe_log(status)
        else:
            self._safe_log(status)

    def _safe_log(self, status):
        """Logs while ensuring the ticker line is cleared."""
        if self._ticker_timer and self._ticker_timer.isActive():
            sys.stdout.write("\r\x1b[K")
            sys.stdout.flush()
        logger.info(status)

    def _handle_completion_milestones(self, status):
        """Finalize the turn timers and latency reporting."""
        was_ticking = self._ticker_timer.isActive() if self._ticker_timer else False
        elapsed = time.time() - self._turn_start_time if self._turn_start_time > 0 else 0

        # Handshake/Latency Lock-in
        if was_ticking and "Response" in status:
            self.stop_ticker()
            # Clear the ticker line BEFORE logging to avoid dual latency artifacts
            sys.stdout.write("\r\x1b[K")
            sys.stdout.flush()

            # Phase 1: Lock in the total latency to the model
            logger.info(f"Latency: {elapsed:.2f}s | {self._ticker_model}")
            # Phase 2: Announce streaming on a fresh line for clarity
            logger.debug(status)

            # Aesthetic Isolation (Top Divider)
            divider = f"\x1b[90m{'—' * 65}\x1b[0m"
            print(divider)

        elif "Complete" in status or "Offloaded" in status:
            # Buffer the completion message instead of printing it immediately
            elapsed = time.time() - self._turn_start_time if self._turn_start_time > 0 else 0
            t_str = time.strftime("%H:%M:%S")
            # Format matching logger SUCCESS
            self._last_completion_msg = (
                f"\x1b[90m{t_str} | \x1b[0m\x1b[32mSUCCESS  \x1b[90m| \x1b[0m{status}"
            )

    def handle_chunk_update(self, payload):
        """Visualizer for AI streaming chunks in the CLI console."""
        if len(payload) < 2:
            return

        chunk = payload[0]
        vector = payload[1]
        metadata = payload[2] if len(payload) > 2 else {}

        if self._ticker_timer and self._ticker_timer.isActive():
            self.stop_ticker()
        if self.terminal:
            return

        self._needs_newline = True
        self.stdout_capture.set_muted(True)
        try:
            # High-Fidelity Rendering: Dim thoughts if metadata is present
            is_thought = metadata.get("is_thought", False) if metadata else False

            if is_thought:
                style = f"{CLI.Style.DIM}\x1b[3m"  # Dim + Italic
                print(f"{style}{chunk}{CLI.Style.RESET_ALL}", end="", flush=True)
            else:
                color = CLI.Fore.CYAN if vector == "a" else CLI.Fore.GREEN
                print(f"{color}{chunk}{CLI.Style.RESET_ALL}", end="", flush=True)
        finally:
            self.stdout_capture.set_muted(False)

    def start_ticker(self, model_name):
        """Initiates the visual handshake ticker."""
        self._ticker_model = model_name
        self._turn_start_time = time.time()
        self._ticker_dots = 0
        self._is_thinking = False
        if self._ticker_timer:
            self._ticker_timer.start(100)

    def stop_ticker(self):
        """Stops the ticker and clears state."""
        if self._ticker_timer and self._ticker_timer.isActive():
            self._ticker_timer.stop()

    def _update_ticker(self):
        """Internal timer callback for the live counter."""
        elapsed = time.time() - self._turn_start_time
        dots = "." * (self._ticker_dots % 4)
        self._ticker_dots += 1

        t_str = time.strftime("%H:%M:%S")
        status_txt = "Thinking" if self._is_thinking else self._ticker_model

        # Format: HH:MM:SS | INFO     | Latency: 0.0s | [Model]...
        # Exact logger color map:
        # Time: \x1b[90m (8 chars) + ' | ' (3 chars) = 11 chars
        # Info Tag: \x1b[0mINFO (Standard) + 4 spaces + literal space = 9 chars
        # Sep: \x1b[90m|
        # Msg: \x1b[34m (Blue)
        line = f"\r\x1b[90m{t_str} | \x1b[0mINFO     \x1b[90m| \x1b[34m{elapsed:.2f}s | {status_txt}{dots: <3}\x1b[0m"

        if hasattr(self.stdout_capture, "_original_stdout"):
            self.stdout_capture._original_stdout.write(line)
            self.stdout_capture._original_stdout.flush()

    def prepare_for_status(self, is_milestone):
        if self._needs_newline and not is_milestone:
            print()
            self._needs_newline = False
