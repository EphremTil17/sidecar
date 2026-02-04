from google import genai
from google.genai import types
from core.config import settings
from core.intelligence.engines.base import BaseEngine

class GeminiEngine(BaseEngine):
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)
        self.use_pro_model = False
        self.chat_session = None
        self.current_system_prompt = ""

    def init_session(self, system_prompt):
        self.current_system_prompt = system_prompt
        model_id = settings.MODEL_PRO if self.use_pro_model else settings.MODEL_FLASH
        
        config = types.GenerateContentConfig(
            system_instruction=self.current_system_prompt,
            temperature=1.0,
            thinking_config=types.ThinkingConfig(
                include_thoughts=True,
                thinking_level=settings.THINKING_LEVEL
            )
        )
        self.chat_session = self.client.chats.create(model=model_id, config=config)

    def stream_analysis(self, png_bytes, additional_text=""):
        if not self.chat_session:
            self.init_session(self.current_system_prompt)

        try:
            content_parts = ["Analyze this view."]
            image_part = types.Part.from_bytes(data=png_bytes, mime_type="image/png")
            content_parts.append(image_part)
            
            if additional_text:
                content_parts.append(f"\n[Additional User Input]: {additional_text}")
            
            return self.chat_session.send_message_stream(message=content_parts)
                    
        except Exception as e:
            def error_gen(): yield f"\n[!] Gemini Error: {e}"
            return error_gen()

    def stream_pivot(self, skill_data, assembled_prompt):
        self.current_system_prompt = assembled_prompt
        override_msg = f"""[SYSTEM OVERRIDE]: Re-tasking sequence initiated. 
# NEW IDENTITY
{skill_data['identity']}
# NEW OPERATIONAL INSTRUCTIONS
{skill_data['instructions']}
# NEW SESSION DATA (CONTEXT)
{skill_data['context']}
Please acknowledge you have absorbed these new instructions."""
        
        try:
            return self.chat_session.send_message_stream(override_msg)
        except Exception as e:
            def error_gen(): yield f"[!] Gemini Pivot Error: {e}"
            return error_gen()

    def get_model_name(self):
        if self.use_pro_model:
            return f"GEMINI PRO ({settings.THINKING_LEVEL})"
        return "GEMINI FLASH"

    def toggle_model(self):
        self.use_pro_model = not self.use_pro_model
        self.init_session(self.current_system_prompt)
        return self.use_pro_model
