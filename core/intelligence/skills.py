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
        """
        skill_path = os.path.join(self.skills_dir, skill_name)
        if not os.path.exists(skill_path):
            return None

        data = {
            "identity": self._read_file(os.path.join(skill_path, "identity.md")),
            "instructions": self._read_file(os.path.join(skill_path, "instructions.md")),
            "context": self._read_file(os.path.join(skill_path, "context.md"))
        }

        # Identify placeholders instead of prompting here
        placeholders = re.findall(r'\{\{(.*?)\}\}', data["context"])
        return data, placeholders

    def create_skill_files(self, skill_name, identity, instructions, context):
        """Pure logic to create skill files."""
        skill_path = os.path.join(self.skills_dir, skill_name)
        if os.path.exists(skill_path):
            return False
        
        os.makedirs(skill_path)
        self._write_file(os.path.join(skill_path, "identity.md"), identity)
        self._write_file(os.path.join(skill_path, "instructions.md"), instructions)
        self._write_file(os.path.join(skill_path, "context.md"), context)
        return True


    def assemble_prompt(self, skill_data):
        """Combines the 3-layer data into a unified, high-performance system prompt with Dialogue Protocol."""
        
        protocol = """
## VERBAL INTERACTION PROTOCOL (Vector T)
When you receive a [CONVERSATION TURN] or transcription context, respond as a high-level human collaborator.
- Tone: Technical, direct, and conversational (like a senior peer pair-programming).
- Format: Use concise bullet points for technical steps or code observations.
- Script Style: Write your response as if perusing a script for a fluid technical dialogue.
- Constraint: Avoid academic verbosity or generic AI filler. Focus purely on actionable insight.
"""

        prompt = f"""# CORE IDENTITY
{skill_data['identity']}

# OPERATIONAL INSTRUCTIONS
{skill_data['instructions']}

# GLOBAL CONVERSATION PROTOCOL
{protocol}

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
