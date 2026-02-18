import base64
import io
import uuid
from collections.abc import Generator

import httpx
from fireworks import Fireworks
from PIL import Image

from core.config import settings
from core.intelligence.engines.base import BaseEngine
from core.intelligence.events import SidecarEvent, SidecarEventType
from core.utils.logger import logger


class FireworksEngine(BaseEngine):
    """
    High-performance Fireworks AI engine (Kimi K2.5 VLM).

    Architecture: Fireworks Native SDK over raw HTTP.
    - SDK-managed streaming with httpx connection pooling.
    - Prompt caching via x-session-affinity header.
    - Image compression (PNG→JPEG) for payload optimization.
    - Built-in retries (2x) for 429/5xx errors.
    """

    # Image compression constants
    MAX_IMAGE_DIMENSION = 1280
    JPEG_QUALITY = 85

    def __init__(self, api_key):
        self.api_key = api_key
        self.model_id = settings.FIREWORKS_MODEL
        self.messages = []
        self.system_prompt = ""
        self._session_id = None

        # Initialize the Fireworks SDK client with optimized timeouts.
        # connect=10s: Generous for cold starts on serverless.
        # read=120s: Allows long token generation without false cutoffs.
        # write=10s: Prompt upload should be fast even with images.
        # pool=10s: Connection pool wait time.
        self.client = Fireworks(
            api_key=api_key,
            timeout=httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=10.0),
            max_retries=2,
        )

    def init_session(self, system_prompt):
        """Standardized session initialization with prompt-cache affinity."""
        self.system_prompt = system_prompt
        self.messages = [{"role": "system", "content": self.system_prompt}]
        # Generate a unique session ID for prompt caching.
        # Fireworks routes requests with the same x-session-affinity
        # to the same GPU, enabling server-side KV-cache reuse.
        self._session_id = str(uuid.uuid4())
        logger.debug(
            f"Fireworks session initialized with model: {self.model_id} "
            f"(session: {self._session_id[:8]}...)"
        )

    def _compress_image(self, png_bytes: bytes) -> str:
        """Compress PNG → JPEG base64, downscaled to max 1280px longest edge.

        Returns a base64-encoded JPEG string. This reduces typical 3MB
        screenshots to ~150KB for faster API transfer.
        """
        img = Image.open(io.BytesIO(png_bytes))

        # Convert RGBA → RGB (JPEG doesn't support alpha)
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")

        # Downscale if larger than threshold
        img.thumbnail(
            (self.MAX_IMAGE_DIMENSION, self.MAX_IMAGE_DIMENSION),
            Image.Resampling.LANCZOS,
        )

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=self.JPEG_QUALITY)
        return base64.b64encode(buf.getvalue()).decode("utf-8")

    def _assemble_multimodal_content(
        self, png_bytes: bytes, additional_text: str, context_images: list | None
    ) -> list:
        """Helper to assemble the multimodal payload for Fireworks."""
        user_content = []

        # 1. VISUAL CONTEXT (Vaulted)
        if context_images:
            user_content.append({"type": "text", "text": "[CONTEXT RECORD]:"})
            for item in context_images:
                b64_img = self._compress_image(item.image_bytes)
                user_content.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"},
                    }
                )

        # 2. PRIMARY VIEW
        if png_bytes:
            b64_primary = self._compress_image(png_bytes)
            user_content.append({"type": "text", "text": "[CURRENT VIEW]:"})
            user_content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64_primary}"},
                }
            )

        # 3. TEXT REQUEST
        user_content.append(
            {
                "type": "text",
                "text": additional_text
                if additional_text
                else "[SIGNAL]: Synthesize all visual context and execute based on active Skill.",
            }
        )
        return user_content

    def add_user_message(self, content: str):
        self.messages.append({"role": "user", "content": content})

    def stream_analysis(
        self,
        png_bytes: bytes,
        additional_text: str = "",
        context_images: list | None = None,
    ) -> Generator[SidecarEvent, None, None]:
        if not self.api_key:
            yield SidecarEvent(SidecarEventType.ERROR, content="Fireworks API Key is missing.")
            return

        # Standardized Context Validation: Allow pure verbal turns, but reject blind turns.
        has_images = bool(png_bytes or context_images)
        if not has_images and not additional_text:
            yield SidecarEvent(
                SidecarEventType.ERROR,
                content="No visual or verbal context provided.",
            )
            return

        user_content = self._assemble_multimodal_content(png_bytes, additional_text, context_images)
        self.messages.append({"role": "user", "content": user_content})

        yield SidecarEvent(
            SidecarEventType.STATUS,
            content=f"HANDSHAKE_START: {self.get_model_name()}",
        )

        try:
            full_response = yield from self._execute_stream()
            if full_response:
                self.messages.append({"role": "assistant", "content": full_response})

            yield SidecarEvent(SidecarEventType.FINISH)
            self.manage_context()

        except Exception as e:
            error_msg = f"Fireworks API Error: {e!s}"
            # Provide specific guidance for common errors
            if "429" in str(e):
                error_msg = f"Fireworks Rate Limited (429). Retries exhausted: {e!s}"
            elif "not found" in str(e).lower() or "model" in str(e).lower():
                error_msg = (
                    f"Model '{self.model_id}' rejected by Fireworks. "
                    "Please verify the ID in the Fireworks panel and .env."
                )
            yield SidecarEvent(SidecarEventType.ERROR, content=error_msg)

    def _execute_stream(self) -> Generator[SidecarEvent, None, str]:
        """Execute the SDK streaming request and yield chunk events.

        Uses the Fireworks native SDK with session affinity for prompt caching.
        The streaming pattern mirrors the Groq engine for consistency.
        """
        # Build request kwargs
        request_kwargs = {
            "model": self.model_id,
            "messages": self.messages,
            "stream": True,
            "max_tokens": 4096,
            "temperature": 0.1,
        }

        # Attach session affinity for prompt caching if available
        if self._session_id:
            request_kwargs["extra_headers"] = {
                "x-session-affinity": self._session_id,
            }

        stream = self.client.chat.completions.create(**request_kwargs)

        full_response = ""
        for chunk in stream:
            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta

            # Handle reasoning/thinking content (if model supports it)
            if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                # Log thinking but don't emit to UI (matches Gemini behavior)
                logger.debug(f"[Fireworks Thinking] {delta.reasoning_content[:80]}...")

            # Handle standard content
            if delta.content:
                full_response += delta.content
                yield SidecarEvent(SidecarEventType.TEXT_CHUNK, content=delta.content)

        return full_response

    def stream_pivot(
        self, skill_data: dict, assembled_prompt: str
    ) -> Generator[SidecarEvent, None, None]:
        self.init_session(assembled_prompt)
        yield SidecarEvent(
            SidecarEventType.TEXT_CHUNK,
            content=f"Fireworks engine re-tasked to {skill_data['identity'][:30]}...",
        )
        yield SidecarEvent(SidecarEventType.FINISH)

    def manage_context(self):
        """Visual Offloading: Neutralizes binary data in history."""
        for msg in self.messages:
            if isinstance(msg.get("content"), list):
                msg["content"] = [
                    p
                    if p.get("type") != "image_url"
                    else {"type": "text", "text": "[OFFLOADED IMAGE: Processed]"}
                    for p in msg["content"]
                ]

    def get_model_name(self):
        return f"FIREWORKS ({self.model_id.split('/')[-1]})"

    def toggle_model(self):
        return False

    def reset_session(self):
        self.messages = []
        self.init_session(self.system_prompt)
