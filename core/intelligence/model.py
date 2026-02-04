from core.config import settings
from core.intelligence.engines.gemini import GeminiEngine
from core.intelligence.engines.groq_engine import GroqEngine

class SidecarBrain:
    def __init__(self, google_api_key, groq_api_key=None):
        self.google_api_key = google_api_key
        self.groq_api_key = groq_api_key
        
        # Initialize engines
        self.engines = {
            "gemini": GeminiEngine(google_api_key),
            "groq": GroqEngine(groq_api_key) if groq_api_key else None
        }
        
        pref = settings.SIDECAR_ENGINE
        if pref == "groq" and not groq_api_key:
            pref = "gemini"
            
        self.active_engine_name = pref
        self.active_engine = self.engines[pref]
        
        self.current_skill_data = None
        self.current_system_prompt = ""

    def set_active_engine(self, name):
        """Sets the active engine by name."""
        if name in self.engines and self.engines[name]:
            self.active_engine_name = name
            self.active_engine = self.engines[name]
        else:
            print(f"[!] Engine {name} not available. Staying on {self.active_engine_name}.")

    def switch_engine(self):
        """Swaps the active engine at runtime."""
        if not self.engines["groq"]:
            return "GROQ key missing - cannot switch."
            
        new_name = "groq" if self.active_engine_name == "gemini" else "gemini"
        self.active_engine_name = new_name
        self.active_engine = self.engines[new_name]
        
        # Important: Initialize the new engine with the current prompt
        self.active_engine.init_session(self.current_system_prompt)
        return f"Switched engine to {new_name.upper()}"

    def set_skill(self, skill_data, assembled_prompt):
        """Sets the current skill and initializes engines."""
        self.current_skill_data = skill_data
        self.current_system_prompt = assembled_prompt
        for name, engine in self.engines.items():
            if engine:
                engine.init_session(assembled_prompt)

    def init_chat(self):
        """Initializes the active engine's session."""
        self.active_engine.init_session(self.current_system_prompt)

    def analyze_image_stream(self, png_bytes, additional_text=""):
        """Streams analysis from the active engine."""
        return self.active_engine.stream_analysis(png_bytes, additional_text)

    def pivot_skill(self, skill_data, assembled_prompt):
        """Pivots the skill for the active engine."""
        self.current_skill_data = skill_data
        self.current_system_prompt = assembled_prompt
        return self.active_engine.stream_pivot(skill_data, assembled_prompt)

    def get_model_name(self):
        """Returns active engine and model details."""
        return self.active_engine.get_model_name()

    def toggle_model(self):
        """Toggles model within the active engine (e.g. Flash/Pro)."""
        return self.active_engine.toggle_model()
