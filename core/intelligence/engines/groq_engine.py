import base64
import json
from typing import Generator
from groq import Groq
from core.config import settings
from core.intelligence.engines.base import BaseEngine
from core.intelligence.events import SidecarEvent, SidecarEventType

class GroqEngine(BaseEngine):
    def __init__(self, api_key):
        self.client = Groq(api_key=api_key)
        self.model_id = settings.GROQ_MODEL
        self.messages = []
        self.system_prompt = ""

    def init_session(self, system_prompt):
        self.system_prompt = system_prompt
        self.messages = [{"role": "system", "content": self.system_prompt}]
        
    def add_user_message(self, content: str):
        self.messages.append({"role": "user", "content": content})

    def stream_analysis(self, png_bytes: bytes, additional_text: str = "") -> Generator[SidecarEvent, None, None]:
        user_content = []
        
        if png_bytes:
            # Convert bytes to base64
            base64_image = base64.b64encode(png_bytes).decode('utf-8')
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{base64_image}"}
            })
            
        # Combine text prompts into one to avoid "Multiple text parts not supported" errors
        text_prompt = "Analyze this view."
        if additional_text:
            text_prompt += f"\n\n[CONVERSATION TURN]: {additional_text}"
        
        user_content.append({"type": "text", "text": text_prompt})

        if not user_content:
             yield SidecarEvent(SidecarEventType.ERROR, content="No context provided.")
             return

        self.messages.append({"role": "user", "content": user_content})
        
        if settings.SAVE_DEBUG_SNAPSHOTS:
            from core.utils.logger import logger
            logger.debug(f"Sending {len(self.messages)} messages to Groq. (Last content size: {len(str(user_content))})")

        # Context Bloat Protection: Blind previous images to save tokens
        scrubbed_messages = []
        for i, msg in enumerate(self.messages):
            if i < len(self.messages) - 1 and isinstance(msg.get("content"), list):
                # Remove image from older turns, leave only text
                text_only = [p for p in msg["content"] if p.get("type") == "text"]
                scrubbed_messages.append({"role": msg["role"], "content": text_only})
            else:
                scrubbed_messages.append(msg)

        yield from self._execute_chat_completion(scrubbed_messages)

    def _execute_chat_completion(self, messages_to_send=None) -> Generator[SidecarEvent, None, None]:
        if messages_to_send is None:
            messages_to_send = self.messages
            
        yield SidecarEvent(SidecarEventType.STATUS, content=f"Initializing {self.model_id} handshake...")
        
        try:
            stream = self.client.chat.completions.create(
                model=self.model_id,
                messages=messages_to_send,
                stream=True,
                max_completion_tokens=4096
            )
            
            yield SidecarEvent(SidecarEventType.STATUS, content="Connection established. Streaming...")
            
            full_response = ""
            for chunk in stream:
                if len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        full_response += delta.content
                        yield SidecarEvent(SidecarEventType.TEXT_CHUNK, content=delta.content)
            
            if full_response:
                self.messages.append({"role": "assistant", "content": full_response})
            
            yield SidecarEvent(SidecarEventType.FINISH)
                    
        except Exception as e:
            error_msg = f"Groq API Error: {str(e)}"
            # Handle model not found specifically
            if "not found" in str(e).lower() or "model" in str(e).lower():
                error_msg = f"Model '{self.model_id}' rejected by Groq. Please verify the ID in the Groq panel and .env."
            yield SidecarEvent(SidecarEventType.ERROR, content=error_msg)

    def stream_pivot(self, skill_data: dict, assembled_prompt: str) -> Generator[SidecarEvent, None, None]:
        self.system_prompt = assembled_prompt
        # Reset history on pivot for Groq to maintain performance/persona focus
        self.init_session(assembled_prompt)
        
        yield SidecarEvent(SidecarEventType.TEXT_CHUNK, content=f"Pivot acknowledged. System re-tasked to {skill_data['identity'][:20]}...")
        yield SidecarEvent(SidecarEventType.FINISH)

    def get_model_name(self):
        return f"GROQ ({self.model_id.split('/')[-1]})"

    def toggle_model(self):
        # Groq engine doesn't currently toggle but we could switch between Maverick and Scout
        print("[i] Groq Maverick is currently fixed for performance.")
        return False
