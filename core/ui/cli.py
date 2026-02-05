from core.utils.editor import NotepadDriver
from core.ui.logo import logo
from colorama import Fore, Style, init

# Initialize colorama for Windows
init(autoreset=True)

class CLI:
    @staticmethod
    def _get_context_status():
        """Builds a condensed status for context vectors."""
        # Using cyan for Pixel and green for Talk to distinguish vectors
        p_status = f"{Fore.CYAN}{Style.BRIGHT}[P]ixel{Style.RESET_ALL}"
        t_status = f"{Fore.GREEN}{Style.BRIGHT}[T]alk{Style.RESET_ALL}"
        return f"{p_status} {Fore.LIGHTBLACK_EX}|{Style.RESET_ALL} {t_status}"

    @staticmethod
    def print_ready():
        """Prints a premium, condensed status bar for the cockpit."""
        divider = f"{Fore.LIGHTBLACK_EX}{'—' * 65}{Style.RESET_ALL}"
        status_text = f"{Fore.YELLOW}{Style.BRIGHT}● READY{Style.RESET_ALL}"
        context_line = CLI._get_context_status()
        
        # Check if transcription context is active (non-empty transcription.txt usually handled in sidecar.py)
        # For the status bar, we show the hotkey hints clearly
        hints = f"{Fore.LIGHTBLACK_EX}Capture: ^!+P  Talk: ^!+T{Style.RESET_ALL}"
        
        print(f"\n{divider}")
        print(f"  {status_text}  {Fore.LIGHTBLACK_EX}::{Style.RESET_ALL}  {context_line}  {Fore.LIGHTBLACK_EX}::{Style.RESET_ALL}  {hints}")
        print(f"{divider}\n")

    @staticmethod
    def select_monitor_menu(available_monitors):
        print("\n--- Available Monitors ---")
        primary_idx = 1
        for mon in available_monitors:
            tag = " (Primary)" if mon['primary'] else ""
            if mon['primary']: primary_idx = mon['index']
            print(f"[{mon['index']}] {mon['name']} [{mon['res']}] {tag}")
        
        print("\nSelect Monitor Index (or press Enter for Primary): ", end="")
        try:
            choice = input().strip()
            if not choice:
                return primary_idx
            return int(choice)
        except ValueError:
            return primary_idx

    @staticmethod
    def select_engine_menu(available_engines):
        print("\n--- Select AI Engine ---")
        for i, engine in enumerate(available_engines):
            print(f"[{i+1}] {engine.upper()}")
        
        print("\nSelection (Default is 1): ", end="")
        try:
            choice = input().strip()
            idx = int(choice) - 1 if choice else 0
            return available_engines[idx] if 0 <= idx < len(available_engines) else available_engines[0]
        except:
            return available_engines[0]

    @staticmethod
    def select_skill_menu(skills):
        print("\n--- Select Initial Skill ---\n")
        for i, s in enumerate(skills):
            print(f"[{i+1}] {s}")
        print(f"[{len(skills)+1}] [+ Create New Skill]")
        
        print("\nSelection (Default is 1): ", end="")
        try:
            choice = input().strip()
            idx = int(choice) - 1 if choice else 0
            
            if idx == len(skills):
                return "NEW_SKILL"
            
            return skills[idx] if 0 <= idx < len(skills) else skills[0]
        except:
            return skills[0]

    @staticmethod
    def skill_pivot_menu(skills):
        print("\n--- SKILL SWAP (Pivot) ---")
        if not skills:
            print("[!] No skills available.")
            return None

        for i, s in enumerate(skills):
            print(f"[{i+1}] {s}")
        
        print("Select Skill Index (or Enter to cancel): ", end="")
        try:
            choice = input().strip()
            if not choice: return None
            
            idx = int(choice) - 1
            return skills[idx] if 0 <= idx < len(skills) else None
        except:
            return None

    @staticmethod
    def session_context_prompt():
        print("\n--- Custom Session Context ---")
        print("Would you like to provide additional context (Resume, JD, Logs) via Notepad? (y/n): ", end="")
        if input().lower().startswith('y'):
            return NotepadDriver.get_input("# PASTE ADDITIONAL CONTEXT HERE\n")
        return None

    @staticmethod
    def print_logo():
        print(logo)
        print("=" * 75)
        print(" " * 30 + "Welcome to SidecarAI")
        print("=" * 75)


    @staticmethod
    def print_welcome(monitor_idx, skill_name, model_name):
        print(f"\n[SYSTEM READY]")
        print(f"Target: Monitor {monitor_idx} | Skill: {skill_name}")
        print(f"Model : {model_name}")
        print("\nPrimary Vectors:")
        print("  [P]ixel: Ctrl + Alt + Shift + P  (Capture Screenshot + File Context)")
        print("  [T]alk:  Ctrl + Alt + Shift + T  (Transcription Follow-up)")
        print("\nManagement:")
        print("  [E]ngine:  Ctrl + Alt + Shift + E")
        print("  [M]odel:   Ctrl + Alt + Shift + M")
        print("  [S]wap:    Ctrl + Alt + Shift + S")
        print("-" * 30)
    @staticmethod
    def prompt_for_variables(skill_name, placeholders):
        print(f"\n[i] Skill '{skill_name}' requires additional input:")
        replacements = {}
        for var in placeholders:
            val = input(f"  Enter value for {var}: ").strip()
            replacements[var] = val
        return replacements

    @staticmethod
    def create_skill_wizard():
        print("\n--- CREATE NEW SKILL ---")
        name = input("Enter Skill Name (e.g., 'coding_expert'): ").strip().lower().replace(" ", "_")
        if not name: return None, None, None, None

        identity = NotepadDriver.get_input("# IDENTITY\nDefine who this agent is...\n") or "You are a helpful assistant."
        instructions = NotepadDriver.get_input("# INSTRUCTIONS\nDefine how this agent works...\n") or "Follow instructions carefully."
        context = NotepadDriver.get_input("# CONTEXT\nProvide background data...\n") or ""
        
        return name, identity, instructions, context
