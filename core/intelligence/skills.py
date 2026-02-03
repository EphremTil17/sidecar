import os
import re

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
