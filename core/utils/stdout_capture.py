import sys
import io
from typing import Callable
from threading import Lock

class StdoutCapture:
    """
    Thread-safe stdout/stderr capture that redirects output to a callback.
    Preserves original stdout for error handling and debugging.
    """
    
    def __init__(self, callback: Callable[[str], None]):
        """
        Initialize stdout capture.
        
        Args:
            callback: Function to call with captured text
        """
        self.callback = callback
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        self._lock = Lock()
        self._active = False
        
    def start(self):
        """Start capturing stdout and stderr."""
        if self._active:
            return
            
        sys.stdout = self._CaptureStream(self.callback, self._original_stdout, self._lock)
        sys.stderr = self._CaptureStream(self.callback, self._original_stderr, self._lock)
        self._active = True
        
    def stop(self):
        """Restore original stdout and stderr."""
        if not self._active:
            return
            
        sys.stdout = self._original_stdout
        sys.stderr = self._original_stderr
        self._active = False
        
    class _CaptureStream(io.TextIOBase):
        """Internal stream wrapper that captures writes."""
        
        def __init__(self, callback: Callable[[str], None], original_stream, lock: Lock):
            self.callback = callback
            self.original_stream = original_stream
            self.lock = lock
            
        def write(self, text: str) -> int:
            """Write text to both callback and original stream."""
            if text:
                with self.lock:
                    # Send to callback (ghost terminal)
                    try:
                        self.callback(text)
                    except Exception:
                        # Silently fail if callback errors (don't break logging)
                        pass
                    
                    # Also write to original stream (for debugging)
                    try:
                        self.original_stream.write(text)
                        self.original_stream.flush()
                    except Exception:
                        pass
                        
            return len(text)
            
        def flush(self):
            """Flush the original stream."""
            try:
                self.original_stream.flush()
            except Exception:
                pass
