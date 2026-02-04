import base64
from groq import Groq
from core.config import settings
from core.intelligence.engines.base import BaseEngine

class GroqEngine(BaseEngine):
    def __init__(self, api_key):
        self.client = Groq(api_key=api_key)
        self.model_id = settings.GROQ_MODEL
        self.messages = []
        self.system_prompt = ""

    def init_session(self, system_prompt):
        self.system_prompt = system_prompt
        self.messages = [{"role": "system", "content": system_prompt}]

    def stream_analysis(self, png_bytes, additional_text=""):
        # Convert bytes to base64
        base64_image = base64.b64encode(png_bytes).decode('utf-8')
        
        user_content = [
            {"type": "text", "text": "Analyze this view."},
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{base64_image}"
                }
            }
        ]
        
        if additional_text:
            user_content.append({"type": "text", "text": f"\n[Additional User Input]: {additional_text}"})

        self.messages.append({"role": "user", "content": user_content})

        try:
            # We use a stream for high-speed feedback
            stream = self.client.chat.completions.create(
                model=self.model_id,
                messages=self.messages,
                stream=True,
                max_completion_tokens=1024
            )
            
            # Since Groq returns a different chunk structure, we wrap it a bit 
            # to make it compatible with the SidecarBrain's expectation of .text/.thought
            def wrapper_gen():
                full_response = ""
                for chunk in stream:
                    content = chunk.choices[0].delta.content
                    if content:
                        full_response += content
                        # Create a duck-typed part and chunk for sidecar interface compatibility
                        class Part: 
                            def __init__(self, t): self.text = t; self.thought = False
                        class Content: 
                            def __init__(self, p): self.parts = [p]
                        class Candidate: 
                            def __init__(self, c): self.content = c
                        class Chunk: 
                            def __init__(self, cand): self.candidates = [cand]
                        
                        yield Chunk(Candidate(Content(Part(content))))
                
                # Append assistant response to history
                self.messages.append({"role": "assistant", "content": full_response})
            
            return wrapper_gen()
                    
        except Exception as e:
            def error_gen(): yield f"\n[!] Groq Error: {e}"
            return error_gen()

    def stream_pivot(self, skill_data, assembled_prompt):
        self.system_prompt = assembled_prompt
        # Reset history on pivot for Groq to maintain performance/persona focus
        self.init_session(assembled_prompt)
        
        def ack_gen():
            # Minimal simulated acknowledgement to match UI flow
            class Part: 
                def __init__(self, t): self.text = t
            class Content: 
                def __init__(self, p): self.parts = [p]
            class Candidate: 
                def __init__(self, c): self.content = c
            class Chunk: 
                def __init__(self, cand): self.candidates = [cand]
            
            yield Chunk(Candidate(Content(Part("Pivot acknowledged. System re-tasked to " + skill_data['identity'][:20] + "..."))))
        
        return ack_gen()

    def get_model_name(self):
        return f"GROQ ({self.model_id.split('/')[-1]})"

    def toggle_model(self):
        # Groq engine doesn't currently toggle but we could switch between Maverick and Scout
        print("[i] Groq Maverick is currently fixed for performance.")
        return False
