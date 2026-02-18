import base64
from typing import Generator
from groq import Groq
from core.config import settings
from core.intelligence.engines.base import BaseEngine
from core.intelligence.events import SidecarEvent, SidecarEventType

class GroqEngine(BaseEngine):
    """
    Groq LPU-powered multimodal engine.
    Optimized for sub-second latency and high-throughput reasoning.
    1:1 logic restoration from v1.13.0 principles.
    """
    def __init__(self, api_key):
        self.api_key = api_key
        self.client = Groq(api_key=api_key)
        self.model_id = settings.GROQ_MODEL
        self.messages = []
        self.system_prompt = ""

    def init_session(self, system_prompt):
        self.system_prompt = system_prompt
        self.messages = [{"role": "system", "content": self.system_prompt}]
        
    def add_user_message(self, content: str):
        self.messages.append({"role": "user", "content": content})

    def stream_analysis(self, png_bytes: bytes, additional_text: str = "", context_images: list = None) -> Generator[SidecarEvent, None, None]:
        user_content = []
        
        # 1. PRIMARY TASK VIEW (Highest Priority)
        if png_bytes:
            base64_image = base64.b64encode(png_bytes).decode('utf-8')
            user_content.append({"type": "text", "text": "[CURRENT VIEW]:"})
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{base64_image}"}
            })

        # 2. SUPPORTING CONTEXT (Supplementary)
        max_total_images = 5
        current_image_count = 1 if png_bytes else 0
        max_context_images = max_total_images - current_image_count
        
        if context_images:
            if len(context_images) > max_context_images:
                yield SidecarEvent(SidecarEventType.STATUS, content=f"Groq Limit: Capping vault to most recent {max_context_images} images.")
                context_images = context_images[-max_context_images:]

            user_content.append({"type": "text", "text": "[CONTEXT VIEW]:"})
            for item in context_images:
                b64_img = base64.b64encode(item.image_bytes).decode('utf-8')
                user_content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64_img}"}
                })

        # 3. VERBAL REQUEST
        user_content.append({"type": "text", "text": additional_text if additional_text else "[SIGNAL]: Synthesize all visual context and execute based on active Skill."})

        if not user_content:
             yield SidecarEvent(SidecarEventType.ERROR, content="No context provided.")
             return

        self.messages.append({"role": "user", "content": user_content})
        
        # v1.13.0 style handshake log
        yield SidecarEvent(SidecarEventType.STATUS, content=f"Handshake with {self.get_model_name()}...")
        yield from self._execute_chat_completion()
        
        # Post-Turn Execution: Visual Offloading (Web-Parity 3.7)
        self.manage_context()

    def _execute_chat_completion(self, messages_to_send=None) -> Generator[SidecarEvent, None, None]:
        if messages_to_send is None:
            messages_to_send = self.messages
        
        try:
            stream = self.client.chat.completions.create(
                model=self.model_id,
                messages=messages_to_send,
                stream=True,
                max_completion_tokens=4096,
                temperature=0.1
            )
            
            # v1.13.0 style connection confirmation
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
            if "not found" in str(e).lower() or "model" in str(e).lower():
                error_msg = f"Model '{self.model_id}' rejected by Groq. Please verify the ID in the Groq panel and .env."
            yield SidecarEvent(SidecarEventType.ERROR, content=error_msg)

    def stream_pivot(self, skill_data: dict, assembled_prompt: str) -> Generator[SidecarEvent, None, None]:
        self.system_prompt = assembled_prompt
        self.init_session(assembled_prompt)
        yield SidecarEvent(SidecarEventType.TEXT_CHUNK, content=f"Pivot acknowledged. System re-tasked to {skill_data['identity'][:20]}...")
        yield SidecarEvent(SidecarEventType.FINISH)

    def get_model_name(self):
        return f"GROQ ({self.model_id.split('/')[-1]})"

    def toggle_model(self):
        return False

    def manage_context(self):
        """Visual Offloading: Neutralizes binary data in history."""
        for msg in self.messages:
            if isinstance(msg.get("content"), list):
                msg["content"] = [
                    p if p.get("type") != "image_url" else {"type": "text", "text": "[OFFLOADED IMAGE: Processed]"}
                    for p in msg["content"]
                ]

    def reset_session(self):
        self.messages = []
        self.init_session(self.system_prompt)
