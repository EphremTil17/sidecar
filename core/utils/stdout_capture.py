import queue
import sys
import threading
from collections.abc import Callable
from contextlib import suppress


class StdoutCapture:
    """
    Thread-safe stdout/stderr capture bridge for UI redirection.

    ARCHITECTURE (Sidecar 3.2):
    Uses a single persistent background 'Drain Thread' to process output
    batches. This prevents the 'Thread Leak' identified in 3.1.
    """

    def __init__(self, callback: Callable[[str], None]):
        self.callback = callback
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        self._lock = threading.RLock()
        self._local = threading.local()
        self._active = False
        self.muted = False

        # Persistent Queue management
        self._queue = queue.Queue()
        self._drain_thread = None
        self._stop_event = threading.Event()

    def start(self):
        """Hijack sys.stdout and sys.stderr and start the drainer."""
        if self._active:
            return

        self._stop_event.clear()
        self._drain_thread = threading.Thread(target=self._drain_loop, daemon=True)
        self._drain_thread.start()

        sys.stdout = self._CaptureStream(
            self.callback, self._original_stdout, self._lock, self._local, self
        )
        sys.stderr = self._CaptureStream(
            self.callback, self._original_stderr, self._lock, self._local, self
        )
        self._active = True

    def stop(self):
        """Restore original system streams and stop the drainer."""
        if not self._active:
            return

        sys.stdout = self._original_stdout
        sys.stderr = self._original_stderr

        self._stop_event.set()
        if self._drain_thread:
            self._drain_thread.join(timeout=0.5)

        self._active = False

    def set_muted(self, muted: bool):
        self.muted = muted

    def _drain_loop(self):
        """Persistent thread that batched and emits captured output."""
        buffer = ""
        while not self._stop_event.is_set():
            try:
                # Wait for at least one item
                chunk = self._queue.get(timeout=0.05)
                buffer += chunk

                # Try to grab remaining items without blocking
                while not self._queue.empty():
                    buffer += self._queue.get_nowait()

                if buffer:
                    self.callback(buffer)
                    buffer = ""

            except queue.Empty:
                continue
            except Exception:
                pass

    class _CaptureStream:
        def __init__(self, callback, original, lock, local_storage, parent):
            self.callback = callback
            self.original = original
            self.lock = lock
            self.local = local_storage
            self.parent = parent

        def write(self, text: str) -> int:
            if not text:
                return 0

            # Phase 1: Direct console path
            try:
                self.original.write(text)
                self.original.flush()
            except Exception:
                pass

            # Phase 2: Queue for UI (Skip if muted)
            if self.parent.muted:
                return len(text)

            if not getattr(self.local, "in_write", False):
                self.local.in_write = True
                try:
                    self.parent._queue.put(text)
                finally:
                    self.local.in_write = False

            return len(text)

        def flush(self):
            with suppress(Exception):
                self.original.flush()

        def __getattr__(self, name):
            return getattr(self.original, name)
