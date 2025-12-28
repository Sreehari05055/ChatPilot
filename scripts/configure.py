#!/usr/bin/env python3
"""Interactive configuration CLI.

Flow: choose provider -> choose model -> enter API key -> write to .env

Requires: InquirerPy, python-dotenv
Install: pip install InquirerPy python-dotenv
"""
from pathlib import Path
import json
import sys

try:
    from InquirerPy import inquirer
except Exception:
    print("InquirerPy is required. Install with: pip install InquirerPy")
    sys.exit(1)

from dotenv import set_key

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
LLM_JSON = ROOT / "configuration" / "llm_models.json"

def ensure_env():
    ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
    ENV_PATH.touch(exist_ok=True)

def load_models():
    if not LLM_JSON.exists():
        return {}
    with open(LLM_JSON, "r", encoding="utf-8") as f:
        return json.load(f)

def write_env_var(key: str, value: str):
    """Write or replace a single KEY=VALUE line in the .env file without extra quotes."""
    # Read existing lines
    lines = []
    if ENV_PATH.exists():
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()

    # Filter out existing key
    prefix = f"{key}="
    new_lines = [l for l in lines if not l.strip().startswith(prefix)]

    # Append new key=value (no quotes)
    new_lines.append(f"{key}={value}\n")

    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.writelines(new_lines)


def remove_env_var(key: str):
    """Remove a KEY= line from the .env file if present."""
    if not ENV_PATH.exists():
        return
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()
    prefix = f"{key}="
    new_lines = [l for l in lines if not l.strip().startswith(prefix)]
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

def main():

    print(r"""
        _____ _           _         _____  _ _        _     
       / ____| |         | |       |  __ \(_) |      | |    
      | |    | |__   ___ | |_      | |__) |_| |  ___ | |_   
      | |    | '_ \ / _ \| __|     |  ___/| | | / _ \| __|  
      | |____| | | | |_| || |      | |    | | || |_| | |_   
       \_____|_| |_|\__|_|\__|     |_|    |_|_| \___/ \__|  
                                                            
                    = ChatPilot Configure =                
    """)

    ensure_env()
    models_map = load_models()
    providers = sorted(list(models_map.keys())) if models_map else ["openai"]

    provider = inquirer.select(
        message="Choose LLM provider:",
        choices=providers,
        default=providers[0],
    ).execute()

    # Ask API key immediately after provider
    api_key = inquirer.secret(message=f"Enter API key for {provider} (will be saved to .env as LLM_API_KEY):").execute()

    # model selection: use curated list if present
    curated = models_map.get(provider, [])
    if curated:
        model = inquirer.fuzzy(
            message=f"Pick a model for {provider} (fuzzy search):",
            choices=curated,
            max_height="60%",
        ).execute()
    else:
        model = inquirer.text(message=f"Enter model name for {provider}:").execute()

    # Collect values and overwrite .env (clear previous values)
    configure_web = inquirer.confirm(message="Enable web search (Google CSE)?", default=False).execute()
    web_key = None
    cse_id = None
    if configure_web:
        web_key = inquirer.secret(message="Enter WEB_SEARCH_API_KEY (leave blank to skip):").execute()
        cse_id = inquirer.text(message="Enter CSE_ID (leave blank to skip):").execute()

    # Overwrite .env file to ensure a clean state
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.write(f"LLM_PROVIDER={provider}\n")
        f.write(f"MODEL_NAME={model}\n")
        f.write(f"LLM_API_KEY={api_key}\n")
        f.write(f"WEB_SEARCH_ENABLED={'true' if configure_web else 'false'}\n")
        if configure_web and web_key:
            f.write(f"WEB_SEARCH_API_KEY={web_key}\n")
        if configure_web and cse_id:
            f.write(f"CSE_ID={cse_id}\n")

    print(f"Wrote configuration to {ENV_PATH}")

if __name__ == "__main__":
    main()
