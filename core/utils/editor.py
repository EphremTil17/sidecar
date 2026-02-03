import os
import subprocess
import tempfile
import time

class NotepadDriver:
    @staticmethod
    def get_input(initial_content="", suffix=".md"):
        """
        Opens a temporary file in Notepad and waits for the user to save and close.
        Returns the content of the file.
        """
        try:
            # Create a temporary file
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False, mode='w', encoding='utf-8') as tf:
                tf.write(initial_content)
                temp_path = tf.name

            # Open in Notepad (Windows specific)
            print(f"[i] Opening editor for input... (Save and Close to continue)")
            process = subprocess.Popen(['notepad.exe', temp_path])
            
            # Wait for the process to finish
            process.wait()

            # Read the content back
            with open(temp_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Clean up
            try:
                os.remove(temp_path)
            except:
                pass

            return content.strip()

        except Exception as e:
            print(f"[!] Error using Notepad driver: {e}")
            return None
