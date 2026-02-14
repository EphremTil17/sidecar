import time
from PyQt6.QtCore import QThread, pyqtSignal, QMutex, QMutexLocker
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
    signal_hud_notification = pyqtSignal(str)   # Logic-to-UI HUD trigger
    signal_heartbeat = pyqtSignal()            # Keep-alive for DWM compositor

    # Slots for true async triggering (Ghost Protocol 2.0)
    trigger_pixel_request = pyqtSignal()
    trigger_verbal_request = pyqtSignal()
    trigger_ingest_request = pyqtSignal()

    def __init__(self, components: dict):
        super().__init__()
        self.brain = components["brain"]
        self.capture_tool = components["capture_tool"]
        self.recorder = components["recorder"]
        self.skill_manager = components["skill_manager"]
        
        # Thread Safety: Use a mutex to prevent race conditions on processing turns
        self._lock = QMutex()
        self.processing_turn = False
        
        # Ghost Protocol 2.0 Hardening:
        # Force the worker object's affinity to ITS OWN thread.
        # This ensures that slots connected to this object's signals 
        # execute in the background event loop, NOT the UI thread.
        self.moveToThread(self)

    def handle_pixel_request(self):
        """Vector P: Triggers screen capture and vision-based analysis."""
        with QMutexLocker(self._lock):
            if self.processing_turn:
                return
            self.processing_turn = True
        
        try:
            start_time = time.time()
            self.signal_status_update.emit("Capturing screen...")
            
            png_bytes = self.capture_tool.capture()
            if not png_bytes: 
                self.signal_chunk_update.emit("[!] Capture Failed.\n", "a")
                return

            self.signal_status_update.emit(f"Analyzing view ({self.brain.get_model_name()})...")
            self.signal_heartbeat.emit() # Initial pulse
            
            stream = self.brain.analyze_image_stream(png_bytes)
            
            first_chunk = True
            for event in stream:
                if event.event_type == SidecarEventType.TEXT_CHUNK and event.content:
                    if first_chunk:
                        latency = time.time() - start_time
                        self.signal_status_update.emit(f"Latency: {latency:.2f}s | Response Streaming...")
                        first_chunk = False
                    self.signal_chunk_update.emit(event.content, "a")
                elif event.event_type == SidecarEventType.STATUS:
                    self.signal_status_update.emit(event.content)
                elif event.event_type == SidecarEventType.ERROR:
                    logger.error(f"Vector A Error: {event.content}")
                    self.signal_chunk_update.emit(f"\n[!] Error: {event.content}\n", "a")
            
            print("\n")
            total_time = time.time() - start_time
            logger.success(f"Vision Analysis Complete. (Total: {total_time:.2f}s)")
            
        except Exception as e:
            logger.error(f"Vector A Exception: {e}")
            self.signal_chunk_update.emit(f"\n[!] Error: {str(e)}\n", "a")
        finally:
            with QMutexLocker(self._lock):
                self.processing_turn = False
            self.signal_status_update.emit("READY")

    def handle_ingest_request(self):
        """Silent Ingestion: Adds context to the brain vault without triggering AI analysis."""
        with QMutexLocker(self._lock):
            if self.processing_turn:
                return None
            
        try:
            png_bytes = self.capture_tool.capture()
            if png_bytes:
                self.brain.add_to_vault(png_bytes)
                logger.info("Visual context successfully added to Vault.")
                return "Information Ingested"
            return "Capture Failed"
        except Exception as e:
            logger.error(f"Ingest Error: {e}")
            return f"Ingest Error: {e}"

    def handle_verbal_request(self):
        """Vector T: Manages audio state (Start/Stop) and triggers transcription analysis."""
        with QMutexLocker(self._lock):
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
                start_time = time.time()
                with QMutexLocker(self._lock):
                    self.processing_turn = True
                self.signal_status_update.emit(f"Processing Intent: {audio_text[:30]}...")
                self.signal_heartbeat.emit() # Initial pulse
                
                stream = self.brain.analyze_verbal_stream(audio_text)
                
                first_chunk = True
                for event in stream:
                    if event.event_type == SidecarEventType.TEXT_CHUNK and event.content:
                        if first_chunk:
                            latency = time.time() - start_time
                            self.signal_status_update.emit(f"Latency: {latency:.2f}s | Response Streaming...")
                            first_chunk = False
                        self.signal_chunk_update.emit(event.content, "b")
                    elif event.event_type == SidecarEventType.STATUS:
                        self.signal_status_update.emit(event.content)
                    elif event.event_type == SidecarEventType.ERROR:
                        logger.error(f"Vector B Error: {event.content}")
                        self.signal_chunk_update.emit(f"\n[!] Error: {event.content}\n", "b")
                
                print("\n")
                total_time = time.time() - start_time
                logger.success(f"Verbal Analysis Complete. (Total: {total_time:.2f}s)")
            else:
                self.signal_status_update.emit("No input detected.")
                
        except Exception as e:
            logger.error(f"Vector B Exception: {e}")
            self.signal_chunk_update.emit(f"\n[!] Error: {str(e)}\n", "b")
        finally:
            if self.recorder.is_idle:
                with QMutexLocker(self._lock):
                    self.processing_turn = False
                self.signal_status_update.emit("READY")

    def run(self):
        """Main event loop for the worker thread."""
        # Connect internal signals to handlers to ensure they run ON THIS THREAD
        self.trigger_pixel_request.connect(self.handle_pixel_request)
        self.trigger_verbal_request.connect(self.handle_verbal_request)
        self.trigger_ingest_request.connect(self._handle_ingest_internal)
        
        logger.info("Sidecar Worker thread active (Ghost Protocol 2.0)")
        self.exec()

    def _handle_ingest_internal(self):
        """Internal bridge for ingestion that emits the HUD signal."""
        msg = self.handle_ingest_request()
        if msg:
            self.signal_hud_notification.emit(msg)
