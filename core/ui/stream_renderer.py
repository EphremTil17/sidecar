from core.intelligence.events import SidecarEventType

class StreamRenderer:
    """
    Handles terminal output formatting for AI response streams.
    Decouples sidecar.py from UI/formatting logic.
    """
    @staticmethod
    def render(stream):
        """Consumes the AI stream and handles think/response formatting with First-Bite overprint."""
        is_thinking = False
        first_bite = True
        
        try:
            for event in stream:
                if event.event_type == SidecarEventType.TEXT_CHUNK:
                    if first_bite:
                        # Clear the "Analyzing..." status and prep for response
                        print(" " * 60, end="\r> ", flush=True)
                        first_bite = False

                    if event.metadata.get("is_thought"):
                        # Handle thinking blocks
                        if not is_thinking:
                            print("\n[THINKING]:", end=" ", flush=True)
                            is_thinking = True
                        print(event.content, end="", flush=True)
                    else:
                        if is_thinking:
                            print("\n\n[RESPONSE]:", end=" ", flush=True)
                            is_thinking = False
                        print(event.content or "", end="", flush=True)

                elif event.event_type == SidecarEventType.ERROR:
                    if first_bite: 
                        print(" " * 60, end="\r", flush=True)
                    print(f"\n[!] Error: {event.content}\n")
                    first_bite = False

                elif event.event_type == SidecarEventType.STATUS:
                    # Status events update the handshake line but don't clear 'first_bite' 
                    # because we haven't started the response yet.
                    print(f"\r{' ' * 60}\r[i] {event.content}", end="", flush=True)
                
        except Exception as e:
            print(f"\n[!] Render Loop Error: {e}\n")
