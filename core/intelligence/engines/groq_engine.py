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

    def stream_analysis(self, png_bytes: bytes, additional_text: str = "", context_images: list = None) -> Generator[SidecarEvent, None, None]:
        user_content = []
        
        # 1. PRIMARY TASK VIEW (Highest Priority)
        # We process the live screenshot first to establish the immediate problem.
        if png_bytes:
            base64_image = base64.b64encode(png_bytes).decode('utf-8')
            user_content.append({"type": "text", "text": "### PRIMARY TASK VIEW (PRIORITY) ###\nThis is the live view of my current screen. Focus your analysis here first."})
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{base64_image}"}
            })

        # 2. SUPPORTING CONTEXT (Supplementary)
        # We cap Groq at 5 total images, leaving 4 slots for vault context.
        max_total_images = 5
        current_image_count = 1 if png_bytes else 0
        max_context_images = max_total_images - current_image_count
        
        if context_images:
            if len(context_images) > max_context_images:
                yield SidecarEvent(SidecarEventType.STATUS, content=f"Groq Limit: Capping vault to most recent {max_context_images} images.")
                context_images = context_images[-max_context_images:]

            user_content.append({"type": "text", "text": "### SUPPLEMENTARY CONTEXT ###\nThe following images are for background documentation and reference only."})
            for item in context_images:
                b64_img = base64.b64encode(item.image_bytes).decode('utf-8')
                user_content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64_img}"}
                })

        # 3. VERBAL REQUEST
        text_prompt = "[USER REQUEST]: " if additional_text else "Solve the Primary Task View using the provided documentation."
        if additional_text:
            text_prompt += additional_text
        user_content.append({"type": "text", "text": text_prompt})

        # Web-Parity 3.7: Memorization Directive
        # Forces the model to transcribe/reference visual data into text for persistent memory.
        if png_bytes or context_images:
            user_content.append({
                "type": "text", 
                "text": "\n[MEMORIZATION DIRECTIVE]: This turn contains vital visual context. "
                        "In your response, ensure you transcribe or reference key details (endpoints, code, logic, etc) "
                        "from the images into your reply. This ensures the information stays in our textual memory "
                        "after the pixels are offloaded."
            })

        if not user_content:
             yield SidecarEvent(SidecarEventType.ERROR, content="No context provided.")
             return

        self.messages.append({"role": "user", "content": user_content})
        
        yield from self._execute_chat_completion()
        
        # Post-Turn Execution: Visual Offloading (Web-Parity 3.7)
        self.manage_context()

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
        # Groq engine doesn't currently toggle but we could switch between model IDs
        return False

    def manage_context(self):
        """
        Visual Offloading (Web-Parity 3.6):
        Strips large visual payloads (base64 images) from previous turns,
        preserving original text turns for infinite context.
        """
        for msg in self.messages:
            if isinstance(msg.get("content"), list):
                # Replace image parts with a lightweight placeholder
                # We skip the very last message as it's the active turn being sent
                msg["content"] = [
                    p if p.get("type") != "image_url" else {"type": "text", "text": "[OFFLOADED IMAGE: Processed]"}
                    for p in msg["content"]
                ]
