import os
from google import genai
from google.genai import types
from core.config import settings

class SidecarBrain:
    def __init__(self, api_key):
        if not api_key:
            raise ValueError("API Key is required")
        
        self.client = genai.Client(api_key=api_key)
        self.use_pro_model = False
        self.chat_session = None
        self.current_skill_data = None
        self.current_system_prompt = ""

    def set_skill(self, skill_data, assembled_prompt):
        """Sets the current skill and its assembled prompt."""
        self.current_skill_data = skill_data
        self.current_system_prompt = assembled_prompt

    def toggle_model(self):
        self.use_pro_model = not self.use_pro_model
        return self.use_pro_model

    def get_model_name(self):
        if self.use_pro_model:
            return f"PRO (Thinking: {settings.THINKING_LEVEL})"
        return "FLASH (Fast)"

    def init_chat(self):
        """Initializes or resets the chat session with the current system prompt."""
        # Check if the chosen model supports thinking (Gemini 3+)
        model_id = settings.MODEL_PRO if self.use_pro_model else settings.MODEL_FLASH
        
        # We enable thinking if include_thoughts is True, and set the level
        # Note: Flash and Pro handle levels slightly differently but 'low'/'high' are common.
        config = types.GenerateContentConfig(
            system_instruction=self.current_system_prompt,
            temperature=1.0,
            thinking_config=types.ThinkingConfig(
                include_thoughts=True,
                thinking_level=settings.THINKING_LEVEL
            )
        )
            
        self.chat_session = self.client.chats.create(model=model_id, config=config)

    def pivot_skill(self, new_skill_data, assembled_prompt):
        """
        Swaps the skill mid-session by sending a hidden override message.
        This preserves conversational history while changing the model's persona/rules.
        """
        self.current_skill_data = new_skill_data
        self.current_system_prompt = assembled_prompt

        override_msg = f"""[SYSTEM OVERRIDE]: Re-tasking sequence initiated. 
Maintain conversation history but update your operational parameters:

# NEW IDENTITY
{new_skill_data['identity']}

# NEW OPERATIONAL INSTRUCTIONS
{new_skill_data['instructions']}

# NEW SESSION DATA (CONTEXT)
{new_skill_data['context']}

Please acknowledge you have absorbed these new instructions and are ready to continue the session with this new persona."""
        
        try:
            # We return the stream so the UI can print the acknowledgement in real-time
            return self.chat_session.send_message_stream(override_msg)
        except Exception as e:
            # Return a generator that yields the error so the UI handling remains consistent
            def error_gen(): yield f"[!] Error during Pivot: {e}"
            return error_gen()

    def analyze_image_stream(self, png_bytes, additional_text=""):
        """Generates a response stream for the given image bytes and optional text."""
        if not self.chat_session:
            self.init_chat()

        try:
            content_parts = ["Analyze this view."]
            
            # Add vision part
            image_part = types.Part.from_bytes(data=png_bytes, mime_type="image/png")
            content_parts.append(image_part)
            
            # Add optional text (e.g. from transcribed audio or notepad)
            if additional_text:
                content_parts.append(f"\n[Additional User Input]: {additional_text}")
            
            return self.chat_session.send_message_stream(message=content_parts)
                    
        except Exception as e:
            def error_gen(): yield f"\n[!] API Error: {e}"
            return error_gen()
