import sys
from core.config import settings
from core.drivers.hotkeys import HotkeyManager
from core.ingestion.orchestrator import RecordingState
from core.utils.system import kill_conflicting_instances
from core.utils.session_manager import SessionManager
from core.ui.stream_renderer import StreamRenderer
from core.ui.cli import CLI

# Global Orchestration Context
brain = None
capture_tool = None
skill_manager = None
audio_ingest = None
recorder = None
processing_turn = False


def handle_pixel_request():
    """Vector A Orchestration: Visual Context Analysis."""
    global brain, capture_tool, audio_ingest, processing_turn
    if processing_turn: return
    processing_turn = True
    
    try:
        # Legacy: Poll for transcription context if available
        audio_text = audio_ingest.poll_for_transcript(clear=False)
        
        print(f"\n{CLI.Fore.CYAN}{'='*60}")
        print(f"{CLI.Fore.CYAN} [ VECTOR A: VISUAL CAPTURE ]")
        print(f"{CLI.Fore.CYAN}{'='*60}\n")
        print(f"{CLI.Fore.YELLOW}[i] Capturing Screen...{CLI.Style.RESET_ALL}", end="", flush=True)
        
        png_bytes = capture_tool.capture()
        if not png_bytes: 
            print(f"{CLI.Fore.RED} [!] Failed.{CLI.Style.RESET_ALL}")
            return

        print(f" ({brain.get_model_name()})\n {CLI.Fore.YELLOW}[i] Analyzing...{CLI.Style.RESET_ALL}", end="\r", flush=True)
        stream = brain.analyze_image_stream(png_bytes, additional_text=audio_text)
        StreamRenderer.render(stream)
        
    finally:
        processing_turn = False
        CLI.print_ready()

def handle_verbal_request():
    """Vector B Orchestration: Stateful Verbal Context."""
    global brain, recorder, processing_turn
    
    # Block concurrent requests unless we are in the middle of a recording toggle
    if processing_turn and not recorder.is_recording: 
        return

    try:
        new_state, audio_text = recorder.toggle()

        if new_state == RecordingState.RECORDING:
            print(f"\n{CLI.Fore.GREEN}{'='*60}")
            print(f"{CLI.Fore.GREEN} [ VECTOR B: VERBAL TURN ]")
            print(f"{CLI.Fore.GREEN}{'='*60}\n")
            print(f"{CLI.Fore.RED}[●] RECORDING... {CLI.Fore.WHITE}(Press T to stop){CLI.Style.RESET_ALL}", end="\r", flush=True)
            return

        elif audio_text:
            processing_turn = True
            print(f"\r{CLI.Fore.GREEN}[i] New Intent: \"{audio_text[:50]}...\"{CLI.Style.RESET_ALL}")
            print(f" {CLI.Fore.YELLOW}[i] Requesting follow-up from {brain.get_model_name()}...{CLI.Style.RESET_ALL}", end="\r", flush=True)
            
            stream = brain.analyze_verbal_stream(audio_text)
            StreamRenderer.render(stream)
        
        else:
            print(f"\r{CLI.Fore.RED}[!] No verbal input detected or recognized.         {CLI.Style.RESET_ALL}")
            
    finally:
        if recorder.is_idle:
            processing_turn = False
            CLI.print_ready()

def handle_toggle_model():
    brain.toggle_model()
    print(f"\n{CLI.Fore.YELLOW}[i] Switched Model to: {CLI.Fore.WHITE}{brain.get_model_name()} {CLI.Fore.YELLOW}(Chat Reset){CLI.Style.RESET_ALL}")
    brain.init_chat()
    CLI.print_ready()

def handle_switch_engine():
    msg = brain.switch_engine()
    print(f"\n{CLI.Fore.YELLOW}[i] {msg} ({brain.get_model_name()}){CLI.Style.RESET_ALL}")
    CLI.print_ready()

def handle_skill_swap():
    skills = skill_manager.list_skills()
    selected = CLI.skill_pivot_menu(skills)
    if selected:
        print(f"{CLI.Fore.CYAN}[i] Loading '{selected}'...{CLI.Style.RESET_ALL}")
        data, placeholders = skill_manager.load_skill(selected)
        
        # Handle Placeholders during pivot
        if placeholders:
            replacements = CLI.prompt_for_variables(selected, placeholders)
            for var, val in replacements.items():
                data["context"] = data["context"].replace(f"{{{{{var}}}}}", val)

        prompt = skill_manager.assemble_prompt(data)
        
        print("\n[SYSTEM]:", end=" ", flush=True)
        stream = brain.pivot_skill(data, prompt)
        StreamRenderer.render(stream)
            
        CLI.print_ready()


def main():
    global brain, capture_tool, recorder, skill_manager, audio_ingest

    # 1. Modular Bootstrap
    session = SessionManager()
    components = session.bootstrap()
    
    brain = components["brain"]
    capture_tool = components["capture_tool"]
    recorder = components["recorder"]
    skill_manager = components["skill_manager"]
    audio_ingest = components["audio_ingest"]

    # 2. Hotkey Binding (Inter-component Wiring)
    hk_manager = HotkeyManager()
    mappings = {
        settings.VK_P: handle_pixel_request,
        settings.VK_M: handle_toggle_model,
        settings.VK_S: handle_skill_swap,
        settings.VK_E: handle_switch_engine,
        settings.VK_T: handle_verbal_request
    }

    for attempt in range(2):
        success = all(hk_manager.register_hotkey(i, vk, cb) for i, (vk, cb) in enumerate(mappings.items()))
        if success: break
        hk_manager.unregister_all()
        if attempt == 0: kill_conflicting_instances()
        else: print(f"{CLI.Fore.RED}[!] Fatal Error: Could not register hotkeys.{CLI.Style.RESET_ALL}"); return

    hk_manager.listen(exit_callback=lambda: print(f"\n{CLI.Fore.YELLOW}[!] Shutting down Cockpit...{CLI.Style.RESET_ALL}"))

if __name__ == "__main__":
    main()
