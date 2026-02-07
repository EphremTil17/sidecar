import sys
import threading
from typing import Callable

class StdoutCapture:
    """
    Thread-safe stdout/stderr capture bridge for UI redirection.
    
    HARDENING NOTE:
    Redirecting stdout to a GUI signal is dangerous because a logging call
    during signal emission can trigger another stdout write, leading to 
    infinite recursion and a stack overflow crash.
    
    The implementation uses:
    1. A thread-local recursion guard ('in_write' flag).
    2. A Recursive Lock (RLock) for multi-threaded safety.
    3. Fast-path writing to the original stream to ensure console logs 
       are never lost even if the GUI bridge fails.
    """
    
    def __init__(self, callback: Callable[[str], None]):
        self.callback = callback
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        self._lock = threading.RLock()
        self._local = threading.local() # Per-thread recursion state
        self._active = False
        
    def start(self):
        """Hijack sys.stdout and sys.stderr with our hardened proxy."""
        if self._active: 
            return
        sys.stdout = self._CaptureStream(self.callback, self._original_stdout, self._lock, self._local)
        sys.stderr = self._CaptureStream(self.callback, self._original_stderr, self._lock, self._local)
        self._active = True
        
    def stop(self):
        """Restore original system streams."""
        if not self._active: 
            return
        sys.stdout = self._original_stdout
        sys.stderr = self._original_stderr
        self._active = False
        
    class _CaptureStream:
        """Lightweight proxy that forwards output to the UI and original stream."""
        def __init__(self, callback, original, lock, local_storage):
            self.callback = callback
            self.original = original
            self.lock = lock
            self.local = local_storage
            
        def write(self, text: str) -> int:
            if not text: 
                return 0
            
            # Phase 1: Direct path to original console (Essential for stability)
            try:
                self.original.write(text)
                self.original.flush()
            except Exception:
                pass
                
            # Phase 2: Redirect to UI (with Recursion Guard)
            # We only emit the signal if we aren't already processing a write from this thread.
            if not getattr(self.local, 'in_write', False):
                self.local.in_write = True
                try:
                    with self.lock:
                        self.callback(text)
                except Exception:
                    pass # Error in UI callback should not break the logger
                finally:
                    self.local.in_write = False
            
            return len(text)
            
        def flush(self):
            try:
                self.original.flush()
            except Exception:
                pass
                
        def __getattr__(self, name):
            """Proxy all other stream attributes (encoding, buffer, etc.) to original."""
            return getattr(self.original, name)
