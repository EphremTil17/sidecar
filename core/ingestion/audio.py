import os

class AudioIngest:
    def __init__(self, transcript_path=None):
        if transcript_path is None:
            self.transcript_path = os.path.join('core', 'ingestion', 'transcripts', 'current.txt')
        else:
            self.transcript_path = transcript_path

    def poll_for_transcript(self):
        """Checks for a transcription from the whisper model handover file and clears it."""
        if os.path.exists(self.transcript_path):
            try:
                with open(self.transcript_path, 'r', encoding='utf-8') as f:
                    text = f.read().strip()
                # Clear it after reading so we don't process it twice
                os.remove(self.transcript_path)
                return text
            except Exception as e:
                print(f"[!] Error reading transcript: {e}")
        return ""
