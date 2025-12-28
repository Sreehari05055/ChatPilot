#!/usr/bin/env python3
"""Admin interactive CLI moved out of the package.

Usage:
  python scripts/admin_manage.py --interactive
"""
import argparse
import os
from InquirerPy import inquirer
from app.core.admin import AdminManager, ToneStyle, ModelConfig, RAGConfig, ChatbotConfig, TONE_TEMPERATURES


def run_interactive():
    admin = AdminManager()
    print(r"""
        _____ _           _         _____  _ _        _     
       / ____| |         | |       |  __ \(_) |      | |    
      | |    | |__   ___ | |_      | |__) |_| |  ___ | |_   
      | |    | '_ \ / _ \| __|     |  ___/| | | / _ \| __|  
      | |____| | | | |_| || |      | |    | | || |_| | |_   
       \_____|_| |_|\__|_|\__|     |_|    |_|_| \___/ \__|  
                                                            
                      = RAG Configurator =                
    """)

    cfg = admin.get_config()
    # Use class defaults for prompts (non-runtime defaults)
    model_defaults = ModelConfig()
    rag_defaults = RAGConfig()
    chatbot_defaults = ChatbotConfig()

    # Tone style selection (uses a select prompt). Selecting a tone suggests a model temperature
    tone_choices = [t.value for t in ToneStyle]
    selected_tone = inquirer.select(
        message=f"Tone style (select to apply suggested temperature and update system prompt):",
        choices=tone_choices,
        default=str(cfg.tone_style),
    ).execute()
    tone_style = selected_tone
    # Suggested temperature based on tone (user can override)
    try:
        suggested_temp = TONE_TEMPERATURES[ToneStyle(tone_style)]
    except Exception:
        suggested_temp = cfg.model.temperature

    # Temperature (float 0.0 - 1.0). Allow empty to keep current value.
    temp_raw = inquirer.text(
        message=f"Temperature (suggested {suggested_temp}) [0.0-1.0] (press Enter to accept suggested):",
        default=str(suggested_temp),
        validate=lambda val: (val.strip() == "") or (0.0 <= float(val) <= 1.0),
        invalid_message="Enter a number between 0.0 and 1.0 or leave blank",
    ).execute()
    try:
        temperature = float(temp_raw) if str(temp_raw).strip() != "" else suggested_temp
    except Exception:
        temperature = suggested_temp

    # top_p (float 0.0 - 1.0)
    top_p_raw = inquirer.text(
        message=f"Top-p [0.0-1.0] (leave blank to keep default: {model_defaults.top_p}):",
        default=str(model_defaults.top_p),
        validate=lambda val: (val.strip() == "") or (0.0 <= float(val) <= 1.0),
        invalid_message="Enter a number between 0.0 and 1.0 or leave blank",
    ).execute()
    try:
        top_p = float(top_p_raw) if str(top_p_raw).strip() != "" else cfg.model.top_p
    except Exception:
        top_p = cfg.model.top_p

    # max_tokens (integer)
    max_tokens = inquirer.number(
        message=f"Max tokens (leave blank to keep default: {model_defaults.max_tokens}):",
        default=model_defaults.max_tokens,
        min_allowed=10,
        max_allowed=10000,
    ).execute()

    # max conversation turns
    max_conversation_turns = inquirer.number(
        message=f"Max conversation turns (leave blank to keep default: {chatbot_defaults.max_conversation_turns}):",
        default=chatbot_defaults.max_conversation_turns,
        min_allowed=10,
        max_allowed=100,
    ).execute()

    # RAG parameters
    chunk_size = inquirer.number(
        message=f"RAG chunk size (leave blank to keep default: {rag_defaults.chunk_size}):",
        default=rag_defaults.chunk_size,
        min_allowed=300,
        max_allowed=800,
    ).execute()
    chunk_overlap = inquirer.number(
        message=f"RAG chunk overlap (leave blank to keep default: {rag_defaults.chunk_overlap}):",
        default=rag_defaults.chunk_overlap,
        min_allowed=20,
        max_allowed=100,
    ).execute()
    top_k = inquirer.number(
        message=f"RAG top_k (leave blank to keep default: {rag_defaults.top_k}):",
        default=rag_defaults.top_k,
        min_allowed=1,
        max_allowed=20,
    ).execute()

    print("\nReview your changes:")
    print(f"  Temperature: {temperature}")
    print(f"  Top-p: {top_p}")
    print(f"  Max tokens: {max_tokens}")
    print(f"  Tone style: {tone_style}")
    print(f"  Max conversation turns: {max_conversation_turns}")
    print(f"  RAG chunk size: {chunk_size}")
    print(f"  RAG chunk overlap: {chunk_overlap}")
    print(f"  RAG top_k: {top_k}")
    confirm = inquirer.confirm(message="Save changes?", default=True).execute()
    if confirm:
        admin.update_model_config(
            temperature=float(temperature),
            top_p=float(top_p),
            max_tokens=int(max_tokens),
        )
        admin.update_style_config(tone_style=tone_style)
        admin.update_rag_config(
            chunk_size=int(chunk_size),
            chunk_overlap=int(chunk_overlap),
            top_k=int(top_k)
        )
        admin.current_config.max_conversation_turns = int(max_conversation_turns)
        admin._save_config()

        prompts_dir = os.path.join(os.path.dirname(__file__), "..", "app", "prompts")
        os.makedirs(prompts_dir, exist_ok=True)
        prompt_path = os.path.join(prompts_dir, "system_prompt.py")
        prompt_str = admin.get_system_prompt_template()
        with open(prompt_path, "w", encoding="utf-8") as f:
            f.write('system_prompt = """\n' + prompt_str.replace('"""', '\"\"\"') + '\n"""\n')
        print("Configuration and system prompt updated and saved!")
    else:
        print("No changes saved.")


if __name__ == '__main__':
    run_interactive()
