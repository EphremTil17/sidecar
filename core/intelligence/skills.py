import re
from pathlib import Path


class SkillManager:
    def __init__(self, skills_dir="skills"):
        self.skills_dir = Path(skills_dir)
        self.ensure_dirs()

    def ensure_dirs(self):
        """Ensures the skills directory exists."""
        if not self.skills_dir.exists():
            self.skills_dir.mkdir(parents=True, exist_ok=True)

    def list_skills(self):
        """Lists all available skill folders, excluding templates."""
        try:
            skills = [
                d.name
                for d in self.skills_dir.iterdir()
                if d.is_dir() and not d.name.startswith("_")
            ]
            return sorted(skills)
        except Exception as e:
            print(f"[!] Error listing skills: {e}")
            return []

    def load_skill(self, skill_name):
        """
        Loads identity, instructions, and context from a skill folder.
        """
        skill_path = self.skills_dir / skill_name
        if not skill_path.exists():
            return None

        data = {
            "identity": self._read_file(skill_path / "identity.md"),
            "instructions": self._read_file(skill_path / "instructions.md"),
            "context": self._read_file(skill_path / "context.md"),
        }

        # Identify placeholders instead of prompting here
        placeholders = re.findall(r"\{\{(.*?)\}\}", data["context"])
        return data, placeholders

    def create_skill_files(self, skill_name, identity, instructions, context):
        """Pure logic to create skill files."""
        skill_path = self.skills_dir / skill_name
        if skill_path.exists():
            return False

        skill_path.mkdir(parents=True, exist_ok=True)
        self._write_file(skill_path / "identity.md", identity)
        self._write_file(skill_path / "instructions.md", instructions)
        self._write_file(skill_path / "context.md", context)
        return True

    def assemble_prompt(self, skill_data):
        """Assembles the system prompt purely from skill data layers with Standardized Patterns."""

        # Standard Operating Patterns: Defines the RELATIONSHIP between vectors, not the persona.
        patterns = """
## CORE INTERACTION PATTERNS
- [CURRENT VIEW]: Represents the primary task or current focus.
- [CONTEXT RECORD]: Represents supporting documentation or historical state (The Vault).
- [USER REQUEST]: Represents the active intent and take priority.

## EXECUTION LOGIC
1. Sequential Priority: User requests (Transcription/Text) define the immediate goal and take priority.
2. Contextual Anchoring: All execution must be grounded in the provided [CURRENT VIEW] and [CONTEXT RECORD].
3. Logic Continuity: If a transcription follows a visual capture or ingestion, treat it as a sequential instruction acting upon that specific data.
4. Auto-Synthesis Requirement: If [CONTEXT RECORD] is provided alongside a [CURRENT VIEW], you must automatically treat this as a signal to re-evaluate the task in the [CURRENT VIEW] using the data/logic found in the [CONTEXT RECORD], regardless of whether a user request is present.
"""

        prompt = f"""# IDENTITY
{skill_data["identity"]}

# STANDARD OPERATING PATTERNS
{patterns}

# SESSION CONTEXT (SKILL DATA)
{skill_data["context"]}

# OPERATIONAL INSTRUCTIONS (SKILL DATA)
{skill_data["instructions"]}
"""
        return prompt

    def _read_file(self, path):
        try:
            if path.exists():
                with path.open(encoding="utf-8") as f:
                    return f.read()
            return ""
        except Exception as e:
            print(f"[!] Error reading {path}: {e}")
            return ""

    def _write_file(self, path, content):
        try:
            with path.open("w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            print(f"[!] Error writing {path}: {e}")
