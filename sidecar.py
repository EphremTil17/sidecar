import sys
import importlib
from core.config import settings
from core.drivers.hotkeys import HotkeyManager
from core.ingestion.screen import ScreenCapture, get_available_monitors
from core.ingestion.audio import AudioIngest
from core.intelligence.model import SidecarBrain
from core.intelligence.skills import SkillManager
from core.intelligence.events import SidecarEventType
from core.utils.system import kill_conflicting_instances
from core.utils.setup import ensure_config
from core.ui.cli import CLI

# Global Components
brain = None
capture_tool = None
skill_manager = None
audio_ingest = None
processing_turn = False


def handle_process_request():
    global processing_turn
    if processing_turn: return
    processing_turn = True
    
    try:
        # Vector A: Visual Turn [P]
        audio_text = audio_ingest.poll_for_transcript(clear=False)
        
        print("\n" + "-"*50)
        print(" [ VECTOR A: VISUAL CAPTURE ]")
        print("-"*50)
        print("[i] Capturing Screen...", end="", flush=True)
        
        png_bytes = capture_tool.capture()
        if not png_bytes: 
            print(" [!] Failed.")
            return

        print(f" ({brain.get_model_name()})\n [i] Analyzing...", end="\r", flush=True)
        stream = brain.analyze_image_stream(png_bytes, additional_text=audio_text)
        _consume_stream(stream)
        
    finally:
        processing_turn = False
        print("\n") # Section Gap
        CLI.print_ready()

def handle_verbal_request():
    global processing_turn
    if processing_turn: return
    processing_turn = True
    
    try:
        # Vector B: Verbal Turn [T]
        print("\n" + "-"*50)
        print(" [ VECTOR B: VERBAL TURN ]")
        print("-" * 50)
        
        # Read the externally managed transcription
        audio_text = audio_ingest.poll_for_transcript(clear=True)
        
        if not audio_text:
            print(f"\r[!] No verbal input detected in: {audio_ingest.transcript_path}")
            return

        print(f"\r[i] New Intent: \"{audio_text[:50]}...\"")
        print(f" [i] Requesting follow-up from {brain.get_model_name()}...", end="\r", flush=True)
        
        stream = brain.analyze_verbal_stream(audio_text)
        _consume_stream(stream)
        
    finally:
        processing_turn = False
        print("\n") # Section Gap
        CLI.print_ready()

def _consume_stream(stream):
    """Consumes the AI stream and handles think/response formatting with First-Bite overprint."""
    is_thinking = False
    first_bite = True
    
    try:
        for event in stream:
            if event.event_type == SidecarEventType.TEXT_CHUNK:
                if first_bite:
                    # Clear the "Analyzing..." status and prep for response
                    print(" " * 60, end="\r> ", flush=True)
                    first_bite = False

                if event.metadata.get("is_thought"):
                    # Handle thinking blocks
                    if not is_thinking:
                        print("\n[THINKING]:", end=" ", flush=True)
                        is_thinking = True
                    print(event.content, end="", flush=True)
                else:
                    if is_thinking:
                        print("\n\n[RESPONSE]:", end=" ", flush=True)
                        is_thinking = False
                    print(event.content or "", end="", flush=True)

            elif event.event_type == SidecarEventType.ERROR:
                if first_bite: 
                    print(" " * 60, end="\r", flush=True)
                print(f"\n[!] Error: {event.content}\n")
                first_bite = False

            elif event.event_type == SidecarEventType.STATUS:
                # Status events update the handshake line but don't clear 'first_bite' 
                # because we haven't started the response yet.
                print(f"\r{' ' * 60}\r[i] {event.content}", end="", flush=True)
            
    except Exception as e:
        print(f"\n[!] Loop Error: {e}\n")

def handle_toggle_model():
    brain.toggle_model()
    print(f"\n[i] Switched Model to: {brain.get_model_name()} (Chat Reset)")
    brain.init_chat()
    CLI.print_ready()

def handle_switch_engine():
    msg = brain.switch_engine()
    print(f"\n[i] {msg} ({brain.get_model_name()})")
    CLI.print_ready()

def handle_skill_swap():
    skills = skill_manager.list_skills()
    selected = CLI.skill_pivot_menu(skills)
    if selected:
        print(f"[i] Loading '{selected}'...")
        data, placeholders = skill_manager.load_skill(selected)
        
        # Handle Placeholders during pivot
        if placeholders:
            replacements = CLI.prompt_for_variables(selected, placeholders)
            for var, val in replacements.items():
                data["context"] = data["context"].replace(f"{{{{{var}}}}}", val)

        prompt = skill_manager.assemble_prompt(data)
        
        print("\n[SYSTEM]:", end=" ", flush=True)
        stream = brain.pivot_skill(data, prompt)
        _consume_stream(stream)
            
        print(f"\n### Skill Swapped to: {selected} ###")
        CLI.print_ready()


def main():
    # Component Initialization

    # 0. Display Branding
    CLI.print_logo()

    # 1. Config & Setup
    if not settings.GOOGLE_API_KEY and not settings.GROQ_API_KEY:
        if not ensure_config():
            sys.exit(1)
        importlib.reload(sys.modules['core.config.settings'])

    # 2. Initialization
    global capture_tool, audio_ingest, brain, skill_manager
    skill_manager = SkillManager()
    monitors = get_available_monitors()
    
    # Always prompt for monitor for precise control (defaults to env-selected index in menu if possible)
    monitor_idx = CLI.select_monitor_menu(monitors)
    
    capture_tool = ScreenCapture(monitor_idx)
    audio_ingest = AudioIngest()
    brain = SidecarBrain(settings.GOOGLE_API_KEY, settings.GROQ_API_KEY)

    # 2.5 Engine Selection
    # Get available engines based on API keys
    available_engines = ["gemini"]
    if settings.GROQ_API_KEY:
        available_engines.append("groq")
    
    # Only prompt if there's more than one engine available
    if len(available_engines) > 1:
        engine_name = CLI.select_engine_menu(available_engines)
        brain.set_active_engine(engine_name)

    # 3. Boot Skills & Context
    skill_name = CLI.select_skill_menu(skill_manager.list_skills())
    
    # Handle New Skill Creation
    if skill_name == "NEW_SKILL":
        name, identity, instructions, context = CLI.create_skill_wizard()
        if name:
            success = skill_manager.create_skill_files(name, identity, instructions, context)
            if success:
                print(f"[SUCCESS] Skill '{name}' created.")
                skill_name = name
            else:
                print(f"[!] Skill folder '{name}' already exists.")
                skill_name = "default"
        else:
            print("[!] Skill creation cancelled.")
            skill_name = "default"
        
    data, placeholders = skill_manager.load_skill(skill_name)
    
    # Handle Placeholders
    if placeholders:
        replacements = CLI.prompt_for_variables(skill_name, placeholders)
        for var, val in replacements.items():
            data["context"] = data["context"].replace(f"{{{{{var}}}}}", val)

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
    CLI.print_ready()

    # 5. Hotkeys
    hk_manager = HotkeyManager()
    callbacks = {
        1: handle_process_request, 
        2: handle_toggle_model, 
        3: handle_skill_swap,
        4: handle_switch_engine,
        5: handle_verbal_request
    }
    vks = {
        1: settings.VK_P, 
        2: settings.VK_M, 
        3: settings.VK_S,
        4: settings.VK_E,
        5: settings.VK_T
    }

    for attempt in range(2):
        # Register Main Hotkeys (Shift+Ctrl+Alt)
        success = all(hk_manager.register_hotkey(i, vks[i], callbacks[i]) for i in callbacks)
        
        if success: break
        hk_manager.unregister_all()
        if attempt == 0: kill_conflicting_instances()
        else: print("[!] Error: Could not register hotkeys."); return

    hk_manager.listen(exit_callback=lambda: print("\n[!] Shutting down..."))

if __name__ == "__main__":
    main()
