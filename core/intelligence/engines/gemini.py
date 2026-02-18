from google import genai
from google.genai import types
from typing import Generator
from core.config import settings
from core.intelligence.engines.base import BaseEngine
from core.intelligence.events import SidecarEvent, SidecarEventType
from core.utils.logger import logger

class GeminiEngine(BaseEngine):
    """
    High-performance Google Gemini 3.0 engine.
    Utilizes the new GenAI SDK for low-latency reasoning and vision.
    Synchronized with latest SDK patterns for Gemini 3 models.
    """
    def __init__(self, api_key):
        self.api_key = api_key
        self.client = genai.Client(api_key=api_key)
        self.use_pro_model = False
        self.chat_session = None
        self.current_system_prompt = ""
        self.model_flash = settings.MODEL_FLASH
        self.model_pro = settings.MODEL_PRO

    def init_session(self, system_prompt):
        """Initializes the chat session with the given system prompt."""
        self.current_system_prompt = system_prompt
        model_id = self.model_pro if self.use_pro_model else self.model_flash
        
        config = types.GenerateContentConfig(
            system_instruction=self.current_system_prompt,
            temperature=1.0,
            thinking_config=types.ThinkingConfig(
                include_thoughts=True,
                thinking_level=settings.THINKING_LEVEL
            )
        )
        self.chat_session = self.client.chats.create(model=model_id, config=config)
        logger.debug(f"Gemini session initialized with model: {model_id}")

    def stream_analysis(self, png_bytes: bytes, additional_text: str = "", context_images: list = None) -> Generator[SidecarEvent, None, None]:
        """
        Multimodal analysis stream (Vector P).
        Handles images and text while managing history.
        """
        if not self.chat_session:
            self.init_session(self.current_system_prompt)

        yield SidecarEvent(SidecarEventType.STATUS, content=f"Handshake with {self.get_model_name()}...")

        try:
            content_parts = []
            
            # 1. PRIMARY TASK VIEW (Highest Priority)
            if png_bytes:
                content_parts.append("[CURRENT VIEW]:")
                image_part = types.Part.from_bytes(data=png_bytes, mime_type="image/png")
                content_parts.append(image_part)
            
            # 2. SUPPORTING CONTEXT (Supplementary)
            if context_images:
                content_parts.append("[CONTEXT RECORD]:")
                for item in context_images:
                    img_part = types.Part.from_bytes(data=item.image_bytes, mime_type="image/png")
                    content_parts.append(img_part)
            
            content_parts.append(f"\n[USER REQUEST]: {additional_text}" if additional_text else "\n[SIGNAL]: Synthesize all visual context and execute based on active Skill.")
            
            if not content_parts:
                 yield SidecarEvent(SidecarEventType.ERROR, content="No visual or verbal context provided.")
                 return
            
            stream = self.chat_session.send_message_stream(message=content_parts)
            for chunk in stream:
                if chunk.candidates[0].content and chunk.candidates[0].content.parts:
                    for part in chunk.candidates[0].content.parts:
                        if part.thought:
                            if settings.VERBOSE_REASONING:
                                # Gemini 3.0 SDK: Thoughts are in part.thought, not part.text
                                yield SidecarEvent(SidecarEventType.TEXT_CHUNK, content=part.thought, metadata={"is_thought": True})
                            else:
                                # Standard: Signal internal 'Thinking' status
                                yield SidecarEvent(SidecarEventType.THOUGHT_CHUNK, content=part.thought)
                        elif part.text:
                            yield SidecarEvent(SidecarEventType.TEXT_CHUNK, content=part.text)
                    
            yield SidecarEvent(SidecarEventType.FINISH)
            
            # Post-Turn Execution: Visual Offloading (Web-Parity 3.0)
            offload_msg = self.manage_context()
            if offload_msg:
                yield SidecarEvent(SidecarEventType.STATUS, content=offload_msg)
            
        except Exception as e:
            yield SidecarEvent(SidecarEventType.ERROR, content=str(e))

    def stream_pivot(self, skill_data: dict, assembled_prompt: str) -> Generator[SidecarEvent, None, None]:
        """Pivots the skill for the session."""
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
            # We send the override message WITHOUT re-initing if possible,
            # but usually, we MUST re-init to apply the new system prompt in config for Gemini 3.0.
            stream = self.chat_session.send_message_stream(override_msg)
            for chunk in stream:
                if chunk.candidates[0].content and chunk.candidates[0].content.parts:
                    for part in chunk.candidates[0].content.parts:
                        if part.text:
                            yield SidecarEvent(SidecarEventType.TEXT_CHUNK, content=part.text)
            yield SidecarEvent(SidecarEventType.FINISH)
        except Exception as e:
            yield SidecarEvent(SidecarEventType.ERROR, content=str(e))

    def get_model_name(self):
        model_id = self.model_pro if self.use_pro_model else self.model_flash
        model_short = model_id.split("/")[-1]
        engine_str = "GEMINI 3.0 PRO" if self.use_pro_model else "GEMINI 3.0 FLASH"
        return f"{engine_str} ({model_short})"

    def toggle_model(self):
        self.use_pro_model = not self.use_pro_model
        self.init_session(self.current_system_prompt)
        return self.use_pro_model

    def add_user_message(self, content: str):
        """No-op: genai.Client manages history statefully."""
        pass

    def manage_context(self):
        """
        Visual Offloading (Web-Parity 3.0):
        Strips heavy binary data (images) from history while keeping the 
        chat session lean and persistent turns textual.
        """
        if not self.chat_session or not hasattr(self.chat_session, '_curated_history'):
            return None

        history = self.chat_session._curated_history
        scrubbed_count = 0
        
        for content in history:
            if hasattr(content, 'parts'):
                new_parts = []
                for p in content.parts:
                    if hasattr(p, 'inline_data') and p.inline_data:
                        new_parts.append(types.Part.from_text(text="[OFFLOADED IMAGE: Processed Context]"))
                        scrubbed_count += 1
                    else:
                        new_parts.append(p)
                content.parts = new_parts

        if scrubbed_count > 0:
            return f"Gemini Visuals Offloaded: {scrubbed_count} image(s) neutralized."
        return None

    def reset_session(self):
        """Hard-reset the chat session."""
        logger.info("Resetting Gemini session...")
        self.chat_session = None
        self.init_session(self.current_system_prompt)
