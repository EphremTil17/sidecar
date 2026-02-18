import time
from PyQt6.QtCore import QThread, QMutex, QMutexLocker
from core.intelligence.events import SidecarEventType
from core.ingestion.orchestrator import RecordingState
from core.utils.logger import logger
from core.types.registry import ComponentRegistry
from core.utils.events import bus, AppEvent

class SidecarWorker(QThread):
    """
    Background worker that runs the SidecarAI processing logic.
    Decouples intensive AI analysis from the GUI main thread to prevent UI freezing.
    """
    
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

    def _process_stream(self, stream, start_time, vector_id):
        """Standardized loop for processing and publishing AI stream events."""
        had_error = False
        first_token_received = False
        
        for event in stream:
            if event.event_type == SidecarEventType.THOUGHT_CHUNK:
                # v1.13.0 compatibility: If thoughts are emitted, we signal thinking.
                bus.publish(AppEvent.AGENT_STATUS_UPDATE, "Thinking")
                # Note: We don't print thoughts unless specifically asked in the engine levels.
                continue

            if event.event_type == SidecarEventType.TEXT_CHUNK and event.content:
                if not first_token_received:
                    first_token_received = True
                    latency = time.time() - start_time
                    bus.publish(AppEvent.AGENT_STATUS_UPDATE, f"Latency: {latency:.2f}s | Response Streaming")
                
                # Web-Parity 3.0: Pass metadata (e.g. is_thought) to the UI layer
                bus.publish(AppEvent.AGENT_CHUNK_UPDATE, (event.content, vector_id, event.metadata))
            elif event.event_type == SidecarEventType.STATUS:
                bus.publish(AppEvent.AGENT_STATUS_UPDATE, event.content)
            elif event.event_type == SidecarEventType.ERROR:
                first_token_received = True
                had_error = True
                logger.error(f"Vector {vector_id.upper()} Error: {event.content}")
                bus.publish(AppEvent.AGENT_CHUNK_UPDATE, (f"\n[!] Error: {event.content}\n", vector_id))
        
        return not had_error

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

            # Web-Parity 3.0: Unified Handshake Event
            bus.publish(AppEvent.AGENT_STATUS_UPDATE, f"HANDSHAKE_START:{self.brain.get_model_name()}")
            bus.publish(AppEvent.AGENT_HEARTBEAT) # Initial pulse
            
            stream = self.brain.analyze_image_stream(png_bytes)
            if self._process_stream(stream, start_time, "a"):
                total_time = time.time() - start_time
                bus.publish(AppEvent.AGENT_STATUS_UPDATE, f"Pixel Analysis Complete. (Total: {total_time:.2f}s)")
                bus.publish(AppEvent.AGENT_HEARTBEAT)
            
        except Exception as e:
            logger.error(f"Vector A Exception: {e}")
            bus.publish(AppEvent.AGENT_CHUNK_UPDATE, (f"\n[!] Critical Exception: {str(e)}\n", "a"))
        finally:
            self._finalize_turn()

    def handle_verbal_request(self):
        """Vector T: Manages audio state (Start/Stop) and triggers transcription analysis."""
        # Safety Lock: Prevent recording if a turn is already processing
        with QMutexLocker(self._lock):
            if self.processing_turn and not self.recorder.is_recording:
                return

        try:
            new_state, audio_text = self.recorder.toggle()
            
            if new_state == RecordingState.RECORDING:
                bus.publish(AppEvent.AGENT_STATUS_UPDATE, "RECORDING...")
                return

            # Transcription Phase
            if audio_text:
                start_time = time.time()
                with QMutexLocker(self._lock):
                    self.processing_turn = True
                
                bus.publish(AppEvent.AGENT_STATUS_UPDATE, f"Processing Intent: {audio_text[:30]}...")
                bus.publish(AppEvent.AGENT_STATUS_UPDATE, f"HANDSHAKE_START:{self.brain.get_model_name()}")
                bus.publish(AppEvent.AGENT_HEARTBEAT)
                
                stream = self.brain.analyze_verbal_stream(audio_text)
                if self._process_stream(stream, start_time, "b"):
                    total_time = time.time() - start_time
                    bus.publish(AppEvent.AGENT_STATUS_UPDATE, f"Verbal Analysis Complete. (Total: {total_time:.2f}s)")
                    bus.publish(AppEvent.AGENT_HEARTBEAT)
            else:
                bus.publish(AppEvent.AGENT_STATUS_UPDATE, "No input detected.")
                
        except Exception as e:
            logger.error(f"Vector B Exception: {e}")
            bus.publish(AppEvent.AGENT_CHUNK_UPDATE, (f"\n[!] Critical Exception: {str(e)}\n", "b"))
        finally:
            if self.recorder.is_idle:
                self._finalize_turn()

    def handle_ingest_request(self):
        """Vector I: Silent context ingestion without triggering AI analysis."""
        with QMutexLocker(self._lock):
            if self.processing_turn:
                return
        
        try:
            bus.publish(AppEvent.AGENT_STATUS_UPDATE, "Context Ingestion: Capturing...")
            png_bytes = self.capture_tool.capture()
            if png_bytes:
                self.brain.add_to_vault(png_bytes)
                msg = "Information Ingested"
                bus.publish(AppEvent.AGENT_STATUS_UPDATE, msg)
                logger.info("Visual context successfully added to Vault.")
            else:
                logger.error("Context Ingestion Failed: Capture error.")
        except Exception as e:
            logger.error(f"Ingestion Exception: {e}")

    def _finalize_turn(self):
        """Releases the turn lock and resets the HUD state."""
        with QMutexLocker(self._lock):
            self.processing_turn = False
        bus.publish(AppEvent.AGENT_STATUS_UPDATE, "READY")

    def run(self):
        """Main event loop for the worker thread."""
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
            self.handle_ingest_request()
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

    def stop(self):
        """Standardized stop for cleanup registration."""
        self.quit()
        self.wait()
