import os
import shutil
import sys
import importlib
from dotenv import load_dotenv, set_key

def ensure_config():
    """
    Ensures .env exists by deploying the template if missing.
    Returns True if API keys are found, False otherwise.
    """
    env_path = ".env"
    template_path = ".env.template"
    
    if not os.path.exists(env_path):
        if os.path.exists(template_path):
            shutil.copy(template_path, env_path)
            print(f"\n[i] Deployed {env_path} from template. (API Keys pending)")
        else:
            print(f"[!] Critical Error: {template_path} missing.")
            sys.exit(1)

    load_dotenv(env_path, override=True)
    # Note: We don't reload settings here to avoid circular imports 
    # if this is called during session bootstrap.
    return bool(os.getenv("GOOGLE_API_KEY") or os.getenv("GROQ_API_KEY"))

def update_env_config(updates: dict):
    """Writes specific key-value pairs to the .env file without destroying comments."""
    env_path = ".env"
    for key, value in updates.items():
        set_key(env_path, key, str(value))
    
    # Reload environment to ensure settings will see the change on next reload
    load_dotenv(env_path, override=True)

def validate_api_keys():
    """Final modular safety check. Ensures at least one thinking engine is available."""
    from core.config import settings
    
    # Define keys to check (Modular for future expansion)
    keys = {
        "GOOGLE_API_KEY": settings.GOOGLE_API_KEY,
        "GROQ_API_KEY": settings.GROQ_API_KEY,
        "FIREWORKS_API_KEY": settings.FIREWORKS_API_KEY
    }
    
    found_any = any(keys.values())

    if not found_any:
        print("\n" + "="*60)
        print("### [ERROR] NO VALID AI ENGINES CONFIGURED ###")
        print("="*60)
        print("Hardware setup finished, but Sidecar found NO thinking models.")
        print("\n[!] DETECTED MISSING KEYS:")
        for name in keys.keys():
            print(f" - {name}")
            
        print("\n[!] ACTION REQUIRED:")
        print("Update your .env file with at least ONE valid API key to proceed.")
        print("="*60 + "\n")
        sys.exit(1)
    else:
        # Report status for found keys
        active = [k for k, v in keys.items() if v]
        print(f"\n[i] AI Infrastructure Validated. (Active: {', '.join(active)})")
