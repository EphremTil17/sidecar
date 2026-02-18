import subprocess
import tempfile
from contextlib import suppress
from pathlib import Path


class NotepadDriver:
    @staticmethod
    def get_input_buffered(initial_content=""):
        """
        Launches Notepad with optional initial content and returns the result
        after the user saves and closes the file.
        """
        with tempfile.NamedTemporaryFile(
            suffix=".txt", delete=False, mode="w", encoding="utf-8"
        ) as tf:
            tf.write(initial_content)
            temp_path = Path(tf.name)

        try:
            # 1. Launch notepad and wait
            subprocess.run(["notepad.exe", str(temp_path)], check=True)

            # 2. Read the content back
            with temp_path.open(encoding="utf-8") as f:
                content = f.read()

            # 3. Clean up
            with suppress(OSError):
                temp_path.unlink()

            return content.strip()
        except Exception as e:
            print(f"[!] Error in Notepad interaction: {e}")
            return initial_content
