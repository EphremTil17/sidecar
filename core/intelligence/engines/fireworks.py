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
        """
        Initializes the chat session.
        Note: The system prompt is kept at index 0 to leverage Fireworks Prompt Caching.
        """
        self.system_prompt = system_prompt
        self.messages = [{"role": "system", "content": self.system_prompt}]
        logger.debug(f"Fireworks session initialized with model: {self.model_id}")

    def add_user_message(self, content: str):
        """Adds a pure text user message (e.g. from Vector T)."""
        self.messages.append({"role": "user", "content": content})

    def stream_analysis(self, png_bytes: bytes, additional_text: str = "", context_images: list = None) -> Generator[SidecarEvent, None, None]:
        """
        Multimodal analysis stream (Vector P).
        Prepend context vault images as supporting material.
        """
        if not self.api_key:
            yield SidecarEvent(SidecarEventType.ERROR, content="Fireworks API Key is missing.")
            return

        user_content = []
        
        # 1. Prepend supporting context from the vault
        if context_images:
            user_content.append({"type": "text", "text": "### SUPPORTING VISUAL CONTEXT ###\n(Background info for the primary task below)"})
            for item in context_images:
                b64_img = base64.b64encode(item.image_bytes).decode('utf-8')
                user_content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64_img}"}
                })
            user_content.append({"type": "text", "text": "\n### END OF CONTEXT ###\n"})

        # 2. Vision Part (Primary Task)
        if png_bytes:
            base64_image = base64.b64encode(png_bytes).decode('utf-8')
            user_content.append({"type": "text", "text": "### PRIMARY TASK VIEW ###"})
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{base64_image}"}
            })

        # 3. Text Part
        text_prompt = "[USER REQUEST]: " if additional_text else "Analyze the Primary Task View using the provided context."
        if additional_text:
            text_prompt += additional_text
        user_content.append({"type": "text", "text": text_prompt})

        self.messages.append({"role": "user", "content": user_content})

        # Context Bloat Protection: 
        # 1. Keep the system prompt (at index 0) for caching.
        # 2. Limit history to the last 10 turns to save tokens/latency.
        # 3. Scrub old images to keep payloads small.
        
        system_msg = self.messages[0]
        history = self.messages[1:]
        
        # Limit history length
        MAX_HISTORY = 20
        if len(history) > MAX_HISTORY:
            history = history[-MAX_HISTORY:]
            
        cleaned_messages = [system_msg]
        for i, msg in enumerate(history):
            # Check if this isn't the very last message in the cleaned list 
            # (which would be our current turn with the image)
            if i < len(history) - 1 and isinstance(msg.get("content"), list):
                text_only = [p for p in msg["content"] if p.get("type") == "text"]
                cleaned_messages.append({"role": msg["role"], "content": text_only})
            else:
                cleaned_messages.append(msg)

        yield from self._execute_request(cleaned_messages)

    def _execute_request(self, messages: list) -> Generator[SidecarEvent, None, None]:
        """Executes the POST request to Fireworks and streams chunks."""
        payload = {
            "model": self.model_id,
            "messages": messages,
            "stream": True,
            "max_tokens": 4096,
            "top_p": 1,
            "top_k": 40,
            "presence_penalty": 0,
            "frequency_penalty": 0,
            "temperature": 0.6,
        }
        
        yield SidecarEvent(SidecarEventType.STATUS, content=f"Consulting {self.model_id.split('/')[-1]}...")

        try:
            # Performance: Re-use the session for faster TTFT
            response = self.session.post(self.url, headers=self.headers, json=payload, stream=True, timeout=30)
            
            if response.status_code != 200:
                error_data = response.text
                try:
                    error_data = response.json().get('error', {}).get('message', response.text)
                except (json.JSONDecodeError, AttributeError, KeyError): 
                    pass
                yield SidecarEvent(SidecarEventType.ERROR, content=f"Fireworks API Error ({response.status_code}): {error_data}")
                return

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

        except Exception as e:
            yield SidecarEvent(SidecarEventType.ERROR, content=f"Fireworks Connection Exception: {str(e)}")

    def stream_pivot(self, skill_data: dict, assembled_prompt: str) -> Generator[SidecarEvent, None, None]:
        """Re-tasking logic."""
        self.init_session(assembled_prompt)
        yield SidecarEvent(SidecarEventType.TEXT_CHUNK, content=f"Fireworks engine re-tasked to {skill_data['identity'][:30]}...")
        yield SidecarEvent(SidecarEventType.FINISH)

    def get_model_name(self):
        return f"FIREWORKS ({self.model_id.split('/')[-1]})"

    def toggle_model(self):
        """Fireworks uses a single high-power model for now."""
        logger.info("Fireworks Kimi-K2P5 is fixed for maximum intelligence.")
        return False
