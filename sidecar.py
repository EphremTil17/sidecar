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
    for text_chunk in stream:
        print(text_chunk, end="", flush=True)
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
        ack = brain.pivot_skill(data, prompt)
        print(f"\n[SYSTEM]: {ack}\n### Skill Swapped to: {selected} ###")

def main():
    global brain, capture_tool, skill_manager

    # 1. Config & Setup
    if not settings.GOOGLE_API_KEY and not ensure_config(): sys.exit(1)
    importlib.reload(sys.modules['core.config.settings'])
    from core.config import settings as settings

    # 2. Initialization
    skill_manager = SkillManager()
    monitors = get_available_monitors()
    monitor_idx = CLI.select_monitor_menu(monitors) if not settings.SIDECAR_MONITOR_INDEX else get_default_monitor_index()
    
    capture_tool = ScreenCapture(monitor_idx)
    brain = SidecarBrain(settings.GOOGLE_API_KEY)

    # 3. Boot Skills & Context
    skill_name = CLI.select_skill_menu(skill_manager.list_skills())
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
