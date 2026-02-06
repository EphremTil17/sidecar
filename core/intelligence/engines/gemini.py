from google import genai
from google.genai import types
from typing import Generator
from core.config import settings
from core.intelligence.engines.base import BaseEngine
from core.intelligence.events import SidecarEvent, SidecarEventType

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

    def stream_analysis(self, png_bytes: bytes, additional_text: str = "") -> Generator[SidecarEvent, None, None]:
        if not self.chat_session:
            self.init_session(self.current_system_prompt)

        try:
            content_parts = []
            if png_bytes:
                content_parts.append("Analyze this view.")
                image_part = types.Part.from_bytes(data=png_bytes, mime_type="image/png")
                content_parts.append(image_part)
            
            if additional_text:
                content_parts.append(f"\n[CONVERSATION TURN]: {additional_text}")
            
            if not content_parts:
                 yield SidecarEvent(SidecarEventType.ERROR, content="No visual or verbal context provided.")
                 return
            
            stream = self.chat_session.send_message_stream(message=content_parts)
            for chunk in stream:
                if chunk.candidates[0].content and chunk.candidates[0].content.parts:
                    for part in chunk.candidates[0].content.parts:
                        if part.thought:
                            yield SidecarEvent(SidecarEventType.TEXT_CHUNK, content=part.text, metadata={"is_thought": True})
                        elif part.text:
                            yield SidecarEvent(SidecarEventType.TEXT_CHUNK, content=part.text)
                    
            yield SidecarEvent(SidecarEventType.FINISH)
                    
        except Exception as e:
            yield SidecarEvent(SidecarEventType.ERROR, content=str(e))

    def stream_pivot(self, skill_data: dict, assembled_prompt: str) -> Generator[SidecarEvent, None, None]:
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
            stream = self.chat_session.send_message_stream(override_msg)
            for chunk in stream:
                for candidate in chunk.candidates:
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                            if part.text:
                                yield SidecarEvent(SidecarEventType.TEXT_CHUNK, content=part.text)
            yield SidecarEvent(SidecarEventType.FINISH)
        except Exception as e:
            yield SidecarEvent(SidecarEventType.ERROR, content=str(e))


    def get_model_name(self):
        if self.use_pro_model:
            return f"GEMINI PRO ({settings.THINKING_LEVEL})"
        return "GEMINI FLASH"

    def toggle_model(self):
        self.use_pro_model = not self.use_pro_model
        self.init_session(self.current_system_prompt)
        return self.use_pro_model

    def add_user_message(self, content: str):
        # The Gemini chat session manages history automatically when send_message is called.
        # If we need to inject history without a response, we'd manually update session.history.
        # But for Sidecar, we usually want the response immediately after transcription.
        pass
