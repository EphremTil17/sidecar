import os

class AudioIngest:
    def __init__(self, transcript_path=None):
        from core.config import settings
        self.transcript_path = transcript_path or settings.TRANSCRIPTION_PATH
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """Creates an empty file if it doesn't exist to satisfy external watchers."""
        if not os.path.exists(self.transcript_path):
            with open(self.transcript_path, 'a', encoding='utf-8') as f:
                pass

    def poll_for_transcript(self, clear=True):
        """Reads the transition file. Assumes the file is ready upon hotkey trigger.
        If clear=True (Vector T), the file content is wiped but the file handle remains.
        If clear=False (Vector P), the file is kept as persistent context.
        """
        if os.path.exists(self.transcript_path):
            try:
                # Use r+ to modify the file in-place without unlinking/replacing it
                with open(self.transcript_path, 'r+', encoding='utf-8') as f:
                    text = f.read().strip()
                    if text and clear:
                        f.seek(0)
                        f.truncate(0)
                    return text
            except Exception as e:
                print(f"[!] Error reading transcript: {e}")
        
        return ""
