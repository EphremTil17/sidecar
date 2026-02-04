from core.utils.editor import NotepadDriver
from core.ui.logo import logo

class CLI:
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
    def select_skill_menu(skills):
        print("\n--- Select Initial Skill ---")
        for i, s in enumerate(skills):
            print(f"[{i+1}] {s}")
        print(f"[{len(skills)+1}] [+ Create New Skill]")
        
        print("Selection (Default is 1): ", end="")
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
        print("\nCommands:")
        print("  [P]rocess: Ctrl + Alt + Shift + P")
        print("  [M]odel:   Ctrl + Alt + Shift + M")
        print("  [S]wap:    Ctrl + Alt + Shift + S")
        print("-" * 30)
