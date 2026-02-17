import time
from PyQt6.QtCore import QThread, QMutex, QMutexLocker
from core.intelligence.events import SidecarEventType
from core.ingestion.orchestrator import RecordingState
from core.utils.logger import logger
from core.types.registry import ComponentRegistry
from core.utils.events import bus, AppEvent, AppState

class SidecarWorker(QThread):
    """
    Background worker that runs the SidecarAI processing logic.
    Decouples intensive AI analysis from the GUI main thread to prevent UI freezing.
    """
    # Logic-to-UI communication is now handled via the AppEventBus (bus)
    # to maintain a strict decoupled architecture.

    def __init__(self, components: ComponentRegistry):
        super().__init__()
        self.brain = components.brain
        self.capture_tool = components.capture_tool
        self.recorder = components.recorder
        self.skill_manager = components.skill_manager
        
        # Thread Safety
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
            bus.publish(AppEvent.AGENT_STATUS_UPDATE, "Capturing screen...")
            
            png_bytes = self.capture_tool.capture()
            if not png_bytes: 
                bus.publish(AppEvent.AGENT_CHUNK_UPDATE, ("[!] Capture Failed.\n", "a"))
                return

            bus.publish(AppEvent.AGENT_STATUS_UPDATE, f"Analyzing view ({self.brain.get_model_name()})...")
            bus.publish(AppEvent.AGENT_HEARTBEAT) # Initial pulse
            
            stream = self.brain.analyze_image_stream(png_bytes)
            
            first_chunk = True
            had_error = False
            for event in stream:
                if event.event_type == SidecarEventType.TEXT_CHUNK and event.content:
                    if first_chunk:
                        latency = time.time() - start_time
                        bus.publish(AppEvent.AGENT_STATUS_UPDATE, f"Latency: {latency:.2f}s | Response Streaming...")
                        first_chunk = False
                    bus.publish(AppEvent.AGENT_CHUNK_UPDATE, (event.content, "a"))
                elif event.event_type == SidecarEventType.STATUS:
                    bus.publish(AppEvent.AGENT_STATUS_UPDATE, event.content)
                elif event.event_type == SidecarEventType.ERROR:
                    had_error = True
                    logger.error(f"Vector A Error: {event.content}")
                    bus.publish(AppEvent.AGENT_CHUNK_UPDATE, (f"\n[!] Error: {event.content}\n", "a"))
            
            if not had_error:
                print("\n")
                total_time = time.time() - start_time
                logger.success(f"Pixel Analysis Complete. (Total: {total_time:.2f}s)")
                bus.publish(AppEvent.AGENT_HEARTBEAT)
            
        except Exception as e:
            logger.error(f"Vector A Exception: {e}")
            bus.publish(AppEvent.AGENT_CHUNK_UPDATE, (f"\n[!] Error: {str(e)}\n", "a"))
        finally:
            with QMutexLocker(self._lock):
                self.processing_turn = False
            bus.publish(AppEvent.AGENT_STATUS_UPDATE, "READY")

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
                bus.publish(AppEvent.AGENT_STATUS_UPDATE, "RECORDING...")
                return

            # Recording stopped, processing transcription
            
            if audio_text:
                start_time = time.time()
                with QMutexLocker(self._lock):
                    self.processing_turn = True
                bus.publish(AppEvent.AGENT_STATUS_UPDATE, f"Processing Intent: {audio_text[:30]}...")
                bus.publish(AppEvent.AGENT_HEARTBEAT) # Initial pulse
                
                stream = self.brain.analyze_verbal_stream(audio_text)
                
                first_chunk = True
                had_error = False
                for event in stream:
                    if event.event_type == SidecarEventType.TEXT_CHUNK and event.content:
                        if first_chunk:
                            latency = time.time() - start_time
                            bus.publish(AppEvent.AGENT_STATUS_UPDATE, f"Latency: {latency:.2f}s | Response Streaming...")
                            first_chunk = False
                        bus.publish(AppEvent.AGENT_CHUNK_UPDATE, (event.content, "b"))
                    elif event.event_type == SidecarEventType.STATUS:
                        bus.publish(AppEvent.AGENT_STATUS_UPDATE, event.content)
                    elif event.event_type == SidecarEventType.ERROR:
                        had_error = True
                        logger.error(f"Vector B Error: {event.content}")
                        bus.publish(AppEvent.AGENT_CHUNK_UPDATE, (f"\n[!] Error: {event.content}\n", "b"))
                
                if not had_error:
                    print("\n")
                    total_time = time.time() - start_time
                    logger.success(f"Verbal Analysis Complete. (Total: {total_time:.2f}s)")
                    bus.publish(AppEvent.AGENT_HEARTBEAT)
            else:
                bus.publish(AppEvent.AGENT_STATUS_UPDATE, "No input detected.")
                
        except Exception as e:
            logger.error(f"Vector B Exception: {e}")
            bus.publish(AppEvent.AGENT_CHUNK_UPDATE, (f"\n[!] Error: {str(e)}\n", "b"))
        finally:
            if self.recorder.is_idle:
                with QMutexLocker(self._lock):
                    self.processing_turn = False
                bus.publish(AppEvent.AGENT_STATUS_UPDATE, "READY")

    def run(self):
        """Main event loop for the worker thread."""
        # Connect to the global Event Bus
        bus.dispatch.connect(self._on_event)
        
        logger.info("Sidecar Worker thread active (Ghost Protocol 2.0)")
        self.exec()

    def _on_event(self, event, payload):
        """Central event dispatcher for the worker thread."""
        if event == AppEvent.TRIGGER_PIXEL:
            self.handle_pixel_request()
        elif event == AppEvent.TRIGGER_TALK:
            self.handle_verbal_request()
        elif event == AppEvent.TRIGGER_INGEST:
            self._handle_ingest_internal()
        elif event == AppEvent.INTELLIGENCE_TOGGLE_MODEL:
            self._handle_model_toggle()
        elif event == AppEvent.INTELLIGENCE_SWITCH_ENGINE:
            self._handle_engine_switch()
        elif event == AppEvent.INTELLIGENCE_SWITCH_SKILL:
            self._handle_skill_switch()

    def _handle_model_toggle(self):
        """Worker-side handler for model toggling (Flash <-> Pro)."""
        self.brain.toggle_model()
        msg = f"Active model: {self.brain.get_model_name()}"
        logger.info(msg)
        bus.publish(AppEvent.AGENT_STATUS_UPDATE, msg)

    def _handle_engine_switch(self):
        """Worker-side handler for engine cycling."""
        msg = self.brain.switch_engine()
        logger.info(msg)
        bus.publish(AppEvent.AGENT_STATUS_UPDATE, msg)

    def _handle_skill_switch(self):
        """Worker-side handler for skill persona rotation."""
        msg = self.brain.switch_skill()
        logger.info(msg)
        bus.publish(AppEvent.AGENT_STATUS_UPDATE, msg)

    def _handle_ingest_internal(self):
        """Internal bridge for ingestion that emits the HUD signal."""
        msg = self.handle_ingest_request()
        if msg:
            bus.publish(AppEvent.AGENT_STATUS_UPDATE, msg)

    def stop(self):
        """Standardized stop for cleanup registration."""
        self.quit()
        self.wait()
