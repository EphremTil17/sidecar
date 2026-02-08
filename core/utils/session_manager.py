import sys
import importlib
from core.config import settings
from core.ingestion.screen import ScreenCapture, get_available_monitors
from core.ingestion.audio_sensor import AudioSensor
from core.ingestion.orchestrator import RecordingOrchestrator
from core.intelligence.model import SidecarBrain
from core.intelligence.transcription_service import TranscriptionService
from core.intelligence.skills import SkillManager
from core.utils.setup import ensure_config
from core.utils.session_cache import SessionCache
from core.utils.hardware_director import HardwareDirector
from core.utils.knowledge_director import KnowledgeDirector
from core.ui.cli import CLI

class SessionManager:
    """
    Director-pattern Orchestrator for SidecarAI bootstrap.
    Coordinates specialized directors for hardware, knowledge, and lifecycle.
    """
    def __init__(self):
        self.skill_manager = SkillManager()
        self.hardware = HardwareDirector()
        self.knowledge = KnowledgeDirector(self.skill_manager)
        
        # State Container
        self.brain = None
        self.capture_tool = None
        self.recorder = None
        self.sensor = None
        
        self._state = {
            "monitor_index": 1,
            "audio_device_id": None,
            "engine_name": settings.SIDECAR_ENGINE,
            "skill_name": "default",
            "skill_placeholders": {},
            "session_context": "",
            "overlay_geometry": None # [x, y, w, h]
        }

    def bootstrap(self) -> dict:
        """Entry point for application lifecycle."""
        CLI.print_logo()

        # 1. Try Fast Boot
        cache = SessionCache.load()
        if cache and self._attempt_fast_boot(cache):
            pass
        else:
            self._full_wizard()

        # 2. Finalize Session
        print("[i] Starting Chat Session...", end="", flush=True)
        self.brain.init_chat()
        print(" Ready.")
        
        self.commit()
        
        CLI.print_welcome(self._state["monitor_index"], self._state["skill_name"], self.brain.get_model_name())
        CLI.print_ready()

        return {
            "brain": self.brain,
            "capture_tool": self.capture_tool,
            "recorder": self.recorder,
            "skill_manager": self.skill_manager
        }

    def _attempt_fast_boot(self, cache: dict) -> bool:
        """Validates and restores session from cache."""
        try:
            # Domain Validation
            if not self.hardware.validate_cache(cache): return False
            if not self.knowledge.validate_cache(cache.get("skill_name")): return False

            # Display Context
            print(f"{CLI.Fore.CYAN}[i] Restoring: {cache.get('skill_name')} | Mon:{cache.get('monitor_index')} | Engine:{cache.get('engine_name')}")
            
            if CLI.wait_for_interrupt():
                return False

            # Restore State
            self._state.update(cache)
            self.hardware.apply_settings(self._state["monitor_index"], self._state["audio_device_id"])
            
            self._init_core_engines()
            self.brain.set_active_engine(self._state["engine_name"])
            
            # Restore Skill
            data, prompt = self.knowledge.restore_skill(
                self._state["skill_name"], 
                self._state["skill_placeholders"],
                self._state["session_context"]
            )
            self.brain.set_skill(data, prompt)
            
            return True
        except Exception as e:
            print(f"[!] Recovery Failed: {e}")
            return False

    def _full_wizard(self):
        """Standard interactive setup."""
        if not settings.GOOGLE_API_KEY and not settings.GROQ_API_KEY:
            if not ensure_config(): sys.exit(1)
            importlib.reload(settings)

        # Hardware
        mon_idx, audio_id = self.hardware.select_hardware()
        self._state["monitor_index"] = mon_idx
        self._state["audio_device_id"] = audio_id
        
        self._init_core_engines()

        # Engine
        self._state["engine_name"] = self._setup_engine_choice()
        self.brain.set_active_engine(self._state["engine_name"])

        # Knowledge
        skill_res = self.knowledge.select_skill()
        self._state.update({
            "skill_name": skill_res["skill_name"],
            "skill_placeholders": skill_res["placeholders"],
            "session_context": skill_res["session_context"]
        })
        self.brain.set_skill(skill_res["data"], skill_res["prompt"])

    def _init_core_engines(self):
        """Initializes hardware and brain components."""
        self.brain = SidecarBrain(settings.GOOGLE_API_KEY, settings.GROQ_API_KEY)
        self.transcription_service = TranscriptionService(settings.GROQ_API_KEY)
        self.capture_tool = ScreenCapture(self._state["monitor_index"])
        self.sensor = AudioSensor()
        self.recorder = RecordingOrchestrator(self.sensor, self.transcription_service)

    def _setup_engine_choice(self):
        available = ["gemini"]
        if settings.GROQ_API_KEY: available.append("groq")
        if settings.FIREWORKS_API_KEY: available.append("fireworks")
        return CLI.select_engine_menu(available) if len(available) > 1 else available[0]

    def commit(self, overlay_geometry=None):
        """Saves current state to persistence layer, syncing from the brain."""
        if self.brain:
            self._state["engine_name"] = self.brain.active_engine_name
            # Skill name is managed by the brain's current_skill_data
            if self.brain.current_skill_data:
                self._state["skill_name"] = self.brain.current_skill_data.get("name", self._state["skill_name"])

        if overlay_geometry:
            self._state["overlay_geometry"] = overlay_geometry
            
        SessionCache.save(self._state)
