import os
from dotenv import load_dotenv

def ensure_config():
    """
    Validates existence of .env and GOOGLE_API_KEY.
    If missing, prompts user and creates the file.
    """
    env_path = ".env"
    
    # 1. Check existing .env
    if os.path.exists(env_path):
        load_dotenv(env_path, override=True)
        if os.getenv("GOOGLE_API_KEY") and os.getenv("GOOGLE_API_KEY").startswith("AIza"):
            return True
    
    # 2. Setup Prompt
    print("\n" + "="*40)
    print("### SIDECAR AI: INITIAL SETUP ###")
    print("="*40)
    print("It looks like your GOOGLE_API_KEY is missing or invalid.")
    print("You can get one for free at: https://aistudio.google.com/app/apikey")
    print("\nPlease enter your Google API Key (AIza...): ", end="")
    
    try:
        api_key = input().strip()
    except EOFError:
        return False
    
    if not api_key or not api_key.startswith("AIza"):
        print("[!] Error: Invalid or empty API Key format.")
        return False
        
    # 3. Write File
    try:
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(f"GOOGLE_API_KEY={api_key}\n")
            f.write("# Monitor index to capture. Default is 1 (Primary).\n")
            f.write("SIDECAR_MONITOR_INDEX=1\n")
            f.write("SIDECAR_DEBUG=False\n")
        
        print(f"\n[SUCCESS] Configuration saved to {env_path}")
        print("[i] Initializing session...")
        print("="*40 + "\n")
        
        # Reload immediately for current process
        load_dotenv(env_path, override=True)
        return True
    except Exception as e:
        print(f"[!] Critical Error writing .env: {e}")
        return False
