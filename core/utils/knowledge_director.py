from core.intelligence.skills import SkillManager
from core.ui.cli import CLI

class KnowledgeDirector:
    """
    Handles skill selection, placeholder injection, and interactive context.
    """
    def __init__(self, skill_manager: SkillManager):
        self.skill_manager = skill_manager

    def select_skill(self):
        """Standard interactive skill setup."""
        skill_name = CLI.select_skill_menu(self.skill_manager.list_skills())
        
        if skill_name == "NEW_SKILL":
            name, identity, instructions, context = CLI.create_skill_wizard()
            if name:
                success = self.skill_manager.create_skill_files(name, identity, instructions, context)
                skill_name = name if success else "default"
            else:
                skill_name = "default"
            
        data, placeholders = self.skill_manager.load_skill(skill_name)
        
        recorded_placeholders = {}
        if placeholders:
            recorded_placeholders = CLI.prompt_for_variables(skill_name, placeholders)
            for var, val in recorded_placeholders.items():
                data["context"] = data["context"].replace(f"{{{{{var}}}}}", val)

        prompt = self.skill_manager.assemble_prompt(data)
        
        # Additional Context
        session_context = CLI.session_context_prompt()
        if session_context:
            data["context"] += f"\n\n## ADDITIONAL INTERACTIVE CONTEXT\n{session_context}"
            prompt = self.skill_manager.assemble_prompt(data)

        return {
            "skill_name": skill_name,
            "placeholders": recorded_placeholders,
            "session_context": session_context,
            "data": data,
            "prompt": prompt
        }

    def restore_skill(self, skill_name: str, placeholders: dict, session_context: str = ""):
        """Restores a skill from cached data."""
        data, _ = self.skill_manager.load_skill(skill_name)
        if not data:
            return None

        # Apply placeholders
        for var, val in placeholders.items():
            data["context"] = data["context"].replace(f"{{{{{var}}}}}", val)
            
        # Apply session context
        if session_context:
            data["context"] += f"\n\n## ADDITIONAL INTERACTIVE CONTEXT\n{session_context}"
            
        prompt = self.skill_manager.assemble_prompt(data)
        return data, prompt

    def validate_cache(self, skill_name: str) -> bool:
        """Checks if cached skill still exists."""
        return skill_name in self.skill_manager.list_skills()
