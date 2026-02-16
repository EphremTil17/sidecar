from google import genai
from google.genai import types
from typing import Generator
from core.config import settings
from core.intelligence.engines.base import BaseEngine
from core.intelligence.events import SidecarEvent, SidecarEventType
from core.utils.logger import logger

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

    def stream_analysis(self, png_bytes: bytes, additional_text: str = "", context_images: list = None) -> Generator[SidecarEvent, None, None]:
        if not self.chat_session:
            self.init_session(self.current_system_prompt)

        try:
            content_parts = []
            
            # 1. Prepend supporting context from the vault
            if context_images:
                content_parts.append("### SUPPORTING VISUAL CONTEXT ###\n(The following images provide background context for my request below)")
                for item in context_images:
                    img_part = types.Part.from_bytes(data=item.image_bytes, mime_type="image/png")
                    content_parts.append(img_part)
                content_parts.append("\n### END OF CONTEXT ###\n")

            # 2. Add current task content
            if png_bytes:
                content_parts.append("### PRIMARY TASK VIEW ###")
                image_part = types.Part.from_bytes(data=png_bytes, mime_type="image/png")
                content_parts.append(image_part)
            
            if additional_text:
                content_parts.append(f"\n[USER REQUEST]: {additional_text}")
            
            if not content_parts:
                 yield SidecarEvent(SidecarEventType.ERROR, content="No visual or verbal context provided.")
                 return
            
            stream = self.chat_session.send_message_stream(message=content_parts)
            for chunk in stream:
                if chunk.candidates[0].content and chunk.candidates[0].content.parts:
                    for part in chunk.candidates[0].content.parts:
                        if part.thought:
                            if settings.VERBOSE_REASONING:
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
        """Adds a user message to the session history (managed by genai.Client)."""
        pass

    def truncate_history(self, max_turns: int = 10):
        """
        Rank-Weighted Truncation (Sidecar 3.0):
        Preserves the conversation start (anchors) and the latest turns (recency),
        while purging the 'Middle-Fog' to save context window.
        """
        if not self.chat_session or not self.chat_session._curated_history:
            return

        history = self.chat_session._curated_history
        if len(history) <= max_turns:
            return

        # Rank 1: Session Anchors (First 2 messages: Initial Greeting/Setup)
        anchors = history[:2]
        
        # Rank 2: Recent Context (The tail of the conversation)
        # We take max_turns - 2 to fill the remaining budget.
        recent_count = max_turns - 2
        recents = history[-recent_count:] if recent_count > 0 else []
        
        # Compact history
        self.chat_session._curated_history = anchors + recents
        logger.info(f"Context Truncated: {len(history)} -> {len(self.chat_session._curated_history)} turns.")
