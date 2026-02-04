import os
import re
from core.utils.editor import NotepadDriver

class SkillManager:
    def __init__(self, skills_dir='skills'):
        self.skills_dir = skills_dir
        self.ensure_dirs()

    def ensure_dirs(self):
        """Ensures the skills directory exists."""
        if not os.path.exists(self.skills_dir):
            os.makedirs(self.skills_dir)

    def list_skills(self):
        """Lists all available skill folders, excluding templates."""
        try:
            items = os.listdir(self.skills_dir)
            skills = [d for d in items if os.path.isdir(os.path.join(self.skills_dir, d)) 
                     and not d.startswith('_')]
            return sorted(skills)
        except Exception as e:
            print(f"[!] Error listing skills: {e}")
            return []

    def load_skill(self, skill_name):
        """
        Loads identity, instructions, and context from a skill folder.
        Assembles them into a coherent system prompt structure.
        """
        skill_path = os.path.join(self.skills_dir, skill_name)
        if not os.path.exists(skill_path):
            return None

        data = {
            "identity": self._read_file(os.path.join(skill_path, "identity.md")),
            "instructions": self._read_file(os.path.join(skill_path, "instructions.md")),
            "context": self._read_file(os.path.join(skill_path, "context.md"))
        }

        # Check for variables in context
        placeholders = re.findall(r'\{\{(.*?)\}\}', data["context"])
        if placeholders:
            print(f"\n[i] Skill '{skill_name}' requires additional input:")
            for var in placeholders:
                # In a real app we might use our editor utility here if it's long
                # For now, simple terminal input for variables
                val = input(f"Enter value for {var}: ").strip()
                data["context"] = data["context"].replace(f"{{{{{var}}}}}", val)

        return data

    def create_new_skill(self):
        """
        Interactively creates a new skill folder and its 3-layer components.
        """
        print("\n--- CREATE NEW SKILL ---")
        skill_name = input("Enter Skill Name (e.g., 'flutter_expert'): ").strip().lower().replace(" ", "_")
        if not skill_name:
            print("[!] Skill creation cancelled.")
            return None

        skill_path = os.path.join(self.skills_dir, skill_name)
        if os.path.exists(skill_path):
            print(f"[!] Skill folder '{skill_name}' already exists.")
            return skill_name

        os.makedirs(skill_path)
        
        # 1. Identity
        identity = NotepadDriver.get_input("# IDENTITY\nDefine who this agent is (e.g., 'You are a senior Flutter engineer...')\n") or "You are a helpful assistant."
        self._write_file(os.path.join(skill_path, "identity.md"), identity)

        # 2. Instructions
        instructions = NotepadDriver.get_input("# INSTRUCTIONS\nDefine how this agent works (e.g., 'Always use clean architecture...')\n") or "Follow user instructions carefully."
        self._write_file(os.path.join(skill_path, "instructions.md"), instructions)

        # 3. Context
        context = NotepadDriver.get_input("# CONTEXT\nProvide background data (e.g., 'The project uses Bloc...')\n") or ""
        self._write_file(os.path.join(skill_path, "context.md"), context)

        print(f"[SUCCESS] Skill '{skill_name}' created at {skill_path}")
        return skill_name

    def assemble_prompt(self, skill_data):
        """Combines the 3-layer data into a single system prompt."""
        prompt = f"""# CORE IDENTITY
{skill_data['identity']}

# OPERATIONAL INSTRUCTIONS
{skill_data['instructions']}

# SESSION CONTEXT
{skill_data['context']}
"""
        return prompt

    def _read_file(self, path):
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return f.read()
            return ""
        except Exception as e:
            print(f"[!] Error reading {path}: {e}")
            return ""

    def _write_file(self, path, content):
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            print(f"[!] Error writing {path}: {e}")
