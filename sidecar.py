import sys
import importlib
from core.config import settings
from core.drivers.hotkeys import HotkeyManager
from core.ingestion.screen import ScreenCapture, get_available_monitors, get_default_monitor_index
from core.ingestion.audio import AudioIngest
from core.intelligence.model import SidecarBrain
from core.intelligence.skills import SkillManager
from core.utils.system import kill_conflicting_instances
from core.utils.setup import ensure_config
from core.ui.cli import CLI

# Global Components
brain = None
capture_tool = None
skill_manager = None
audio_ingest = AudioIngest()

def handle_process_request():
    audio_text = audio_ingest.poll_for_transcript()
    print("\n[O] Capturing...", end="", flush=True)
    png_bytes = capture_tool.capture()
    if not png_bytes: return

    print(f" ({brain.get_model_name()})\n Analyzing...", end="\r", flush=True)
    stream = brain.analyze_image_stream(png_bytes, additional_text=audio_text)
    
    print(" " * 30, end="\r> ")
    is_thinking = False
    
    try:
        for chunk in stream:
            # The google-genai SDK response chunk has candidates -> content -> parts
            for candidate in chunk.candidates:
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        # Thoughts
                        if part.thought:
                            if not is_thinking:
                                print("\n[THINKING]:", end=" ", flush=True)
                                is_thinking = True
                            print(part.text, end="", flush=True)
                        
                        # Final Text
                        elif part.text:
                            if is_thinking:
                                print("\n\n[RESPONSE]:", end=" ", flush=True)
                                is_thinking = False
                            print(part.text, end="", flush=True)
    except Exception as e:
        print(f"\n[!] Stream Error: {e}")
    print("\n")

def handle_toggle_model():
    brain.toggle_model()
    print(f"\n[i] Switched Model to: {brain.get_model_name()} (Chat Reset)")
    brain.init_chat()

def handle_skill_swap():
    skills = skill_manager.list_skills()
    selected = CLI.skill_pivot_menu(skills)
    if selected:
        print(f"[i] Loading '{selected}'...")
        data = skill_manager.load_skill(selected)
        prompt = skill_manager.assemble_prompt(data)
        
        print("\n[SYSTEM]:", end=" ", flush=True)
        stream = brain.pivot_skill(data, prompt)
        try:
            for chunk in stream:
                for candidate in chunk.candidates:
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                            if part.text:
                                print(part.text, end="", flush=True)
        except Exception as e:
            print(f"\n[!] Pivot Error: {e}")
            
        print(f"\n### Skill Swapped to: {selected} ###\n")

def main():
    global brain, capture_tool, skill_manager

    # 0. Display Branding
    CLI.print_logo()

    # 1. Config & Setup
    if not settings.GOOGLE_API_KEY:
        if not ensure_config():
            sys.exit(1)
        importlib.reload(sys.modules['core.config.settings'])

    # 2. Initialization
    skill_manager = SkillManager()
    monitors = get_available_monitors()
    
    # Always prompt for monitor unless SIDECAR_MONITOR_INDEX is explicitly set to skip (or use get_default_monitor_index)
    if not settings.SIDECAR_MONITOR_INDEX:
        monitor_idx = CLI.select_monitor_menu(monitors)
    else:
        # If it's in the env, we can still show the menu but default to it, 
        # or just skip if the user is happy. Let's make it prompt by default for better control.
        # monitor_idx = get_default_monitor_index()
        monitor_idx = CLI.select_monitor_menu(monitors)
    
    capture_tool = ScreenCapture(monitor_idx)
    brain = SidecarBrain(settings.GOOGLE_API_KEY)

    # 3. Boot Skills & Context
    skill_name = CLI.select_skill_menu(skill_manager.list_skills())
    
    # Handle New Skill Creation
    if skill_name == "NEW_SKILL":
        skill_name = skill_manager.create_new_skill()
        if not skill_name: skill_name = "default" # Fallback
        
    data = skill_manager.load_skill(skill_name)
    prompt = skill_manager.assemble_prompt(data)
    brain.set_skill(data, prompt)

    extra_ctx = CLI.session_context_prompt()
    if extra_ctx:
        data["context"] += f"\n\n## ADDITIONAL INTERACTIVE CONTEXT\n{extra_ctx}"
        brain.set_skill(data, skill_manager.assemble_prompt(data))

    # 4. Start Session
    print("[i] Starting Chat Session...", end="", flush=True)
    brain.init_chat()
    print(" Ready.")
    
    CLI.print_welcome(monitor_idx, skill_name, brain.get_model_name())

    # 5. Hotkeys
    hk_manager = HotkeyManager()
    callbacks = {1: handle_process_request, 2: handle_toggle_model, 3: handle_skill_swap}
    vks = {1: settings.VK_P, 2: settings.VK_M, 3: settings.VK_S}

    for attempt in range(2):
        if all(hk_manager.register_hotkey(i, vks[i], callbacks[i]) for i in callbacks): break
        hk_manager.unregister_all()
        if attempt == 0: kill_conflicting_instances()
        else: print("[!] Error: Could not register hotkeys."); return

    hk_manager.listen(exit_callback=lambda: print("\n[!] Shutting down..."))

if __name__ == "__main__":
    main()
