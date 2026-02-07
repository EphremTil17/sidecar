from PyQt6.QtCore import QThread, pyqtSignal
from core.intelligence.model import SidecarBrain
from core.intelligence.events import SidecarEventType
from core.ingestion.orchestrator import RecordingState
from core.utils.logger import logger

class SidecarWorker(QThread):
    """
    Background worker that runs the SidecarAI processing logic.
    Decouples intensive AI analysis from the GUI main thread to prevent UI freezing.
    """
    signal_chunk_update = pyqtSignal(str, str)  # Stream text chunks to UI
    signal_status_update = pyqtSignal(str)      # Update UI status text
    signal_recording_toggle = pyqtSignal(bool)  # Sync recording UI state

    def __init__(self, components: dict):
        super().__init__()
        self.brain = components["brain"]
        self.capture_tool = components["capture_tool"]
        self.recorder = components["recorder"]
        self.skill_manager = components["skill_manager"]
        self.processing_turn = False

    def handle_pixel_request(self):
        """Vector P: Triggers screen capture and vision-based analysis."""
        if self.processing_turn:
            return
        self.processing_turn = True
        
        try:
            self.signal_status_update.emit("Capturing screen...")
            
            png_bytes = self.capture_tool.capture()
            if not png_bytes: 
                self.signal_chunk_update.emit("[!] Capture Failed.\n", "a")
                return

            self.signal_status_update.emit(f"Analyzing view ({self.brain.get_model_name()})...")
            stream = self.brain.analyze_image_stream(png_bytes)
            
            for event in stream:
                if event.event_type == SidecarEventType.TEXT_CHUNK and event.content:
                    self.signal_chunk_update.emit(event.content, "a")
                elif event.event_type == SidecarEventType.STATUS:
                    self.signal_status_update.emit(event.content)
                elif event.event_type == SidecarEventType.ERROR:
                    logger.error(f"Vector A Error: {event.content}")
                    self.signal_chunk_update.emit(f"\n[!] Error: {event.content}\n", "a")
            
            print("\n")
            logger.success("Vision Analysis Complete.")
            
        except Exception as e:
            logger.error(f"Vector A Exception: {e}")
            self.signal_chunk_update.emit(f"\n[!] Error: {str(e)}\n", "a")
        finally:
            self.processing_turn = False
            self.signal_status_update.emit("READY")

    def handle_verbal_request(self):
        """Vector T: Manages audio state (Start/Stop) and triggers transcription analysis."""
        if self.processing_turn and not self.recorder.is_recording:
            return

        try:
            new_state, audio_text = self.recorder.toggle()
            
            if new_state == RecordingState.RECORDING:
                self.signal_recording_toggle.emit(True)
                self.signal_status_update.emit("RECORDING...")
                return

            self.signal_recording_toggle.emit(False)
            
            if audio_text:
                self.processing_turn = True
                self.signal_status_update.emit(f"Processing Intent: {audio_text[:30]}...")
                
                stream = self.brain.analyze_verbal_stream(audio_text)
                
                for event in stream:
                    if event.event_type == SidecarEventType.TEXT_CHUNK and event.content:
                        self.signal_chunk_update.emit(event.content, "b")
                    elif event.event_type == SidecarEventType.STATUS:
                        self.signal_status_update.emit(event.content)
                    elif event.event_type == SidecarEventType.ERROR:
                        logger.error(f"Vector B Error: {event.content}")
                        self.signal_chunk_update.emit(f"\n[!] Error: {event.content}\n", "b")
                
                print("\n")
                logger.success("Verbal Analysis Complete.")
            else:
                self.signal_status_update.emit("No input detected.")
                
        except Exception as e:
            logger.error(f"Vector B Exception: {e}")
            self.signal_chunk_update.emit(f"\n[!] Error: {str(e)}\n", "b")
        finally:
            if self.recorder.is_idle:
                self.processing_turn = False
                self.signal_status_update.emit("READY")

    def run(self):
        """Main event loop for the worker thread."""
        logger.info("Sidecar Worker thread active.")
        self.exec()
