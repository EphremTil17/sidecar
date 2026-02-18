import base64
import json
import requests
from typing import Generator
from core.config import settings
from core.intelligence.engines.base import BaseEngine
from core.intelligence.events import SidecarEvent, SidecarEventType
from core.utils.logger import logger

class FireworksEngine(BaseEngine):
    """
    High-performance Fireworks AI engine implementation.
    Optimized for kimi-k2p5 vision-language model with prompt caching.
    1:1 logic restoration from v1.13.0 principles.
    """
    def __init__(self, api_key):
        self.api_key = api_key
        self.url = "https://api.fireworks.ai/inference/v1/chat/completions"
        self.model_id = settings.FIREWORKS_MODEL
        self.messages = []
        self.system_prompt = ""
        
        # Performance: Use a persistent session to keep the TCP/TLS connection warm
        self.session = requests.Session()
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

    def init_session(self, system_prompt):
        """Standardized session initialization."""
        self.system_prompt = system_prompt
        self.messages = [{"role": "system", "content": self.system_prompt}]
        logger.debug(f"Fireworks session initialized with model: {self.model_id}")

    def add_user_message(self, content: str):
        self.messages.append({"role": "user", "content": content})

    def stream_analysis(self, png_bytes: bytes, additional_text: str = "", context_images: list = None) -> Generator[SidecarEvent, None, None]:
        if not self.api_key:
            yield SidecarEvent(SidecarEventType.ERROR, content="Fireworks API Key is missing.")
            return

        user_content = []
        
        # 1. VISUAL CONTEXT (Vaulted)
        if context_images:
            user_content.append({"type": "text", "text": "[CONTEXT RECORD]:"})
            for item in context_images:
                b64_img = base64.b64encode(item.image_bytes).decode('utf-8')
                user_content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64_img}"}
                })

        # 2. PRIMARY VIEW
        if png_bytes:
            base64_image = base64.b64encode(png_bytes).decode('utf-8')
            user_content.append({"type": "text", "text": "[CURRENT VIEW]:"})
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{base64_image}"}
            })

        # 3. TEXT REQUEST
        user_content.append({"type": "text", "text": additional_text if additional_text else "[SIGNAL]: Synthesize all visual context and execute based on active Skill."})

        self.messages.append({"role": "user", "content": user_content})

        yield SidecarEvent(SidecarEventType.STATUS, content=f"Handshake with {self.get_model_name()}...")

        payload = {
            "model": self.model_id,
            "messages": self.messages,
            "stream": True,
            "max_tokens": 4096,
            "temperature": 0.1,
        }

        try:
            response = self.session.post(self.url, headers=self.headers, json=payload, stream=True, timeout=30)
            
            if response.status_code != 200:
                error_data = response.text
                yield SidecarEvent(SidecarEventType.ERROR, content=f"Fireworks API Error ({response.status_code}): {error_data}")
                return

            # v1.13.0 style connection confirmation
            yield SidecarEvent(SidecarEventType.STATUS, content="Connection established. Streaming...")

            full_response = ""
            for line in response.iter_lines():
                if not line:
                    continue
                line_text = line.decode('utf-8')
                if line_text.startswith("data: "):
                    data_str = line_text[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        if chunk.get("choices") and chunk["choices"][0].get("delta", {}).get("content"):
                            content = chunk["choices"][0]["delta"]["content"]
                            full_response += content
                            yield SidecarEvent(SidecarEventType.TEXT_CHUNK, content=content)
                    except json.JSONDecodeError:
                        continue

            if full_response:
                self.messages.append({"role": "assistant", "content": full_response})
            
            yield SidecarEvent(SidecarEventType.FINISH)
            self.manage_context()

        except Exception as e:
            yield SidecarEvent(SidecarEventType.ERROR, content=f"Fireworks Connection Exception: {str(e)}")

    def stream_pivot(self, skill_data: dict, assembled_prompt: str) -> Generator[SidecarEvent, None, None]:
        self.init_session(assembled_prompt)
        yield SidecarEvent(SidecarEventType.TEXT_CHUNK, content=f"Fireworks engine re-tasked to {skill_data['identity'][:30]}...")
        yield SidecarEvent(SidecarEventType.FINISH)

    def manage_context(self):
        for msg in self.messages:
            if isinstance(msg.get("content"), list):
                msg["content"] = [
                    p if p.get("type") != "image_url" else {"type": "text", "text": "[OFFLOADED IMAGE: Processed]"}
                    for p in msg["content"]
                ]

    def get_model_name(self):
        return f"FIREWORKS ({self.model_id.split('/')[-1]})"

    def toggle_model(self):
        return False

    def reset_session(self):
         self.messages = []
         self.init_session(self.system_prompt)
