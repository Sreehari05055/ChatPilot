from typing import Any
from app.services.llm_engine.anthropic_engine import AnthropicEngine
from app.services.llm_engine.openai_engine import OpenAIEngine
from app.services.llm_engine.deepseek_engine import DeepseekEngine

def create_llm_engine(provider: str, client: Any):
    """Factory for creating LLM engine instances.

    Extend this function to support additional providers (e.g., Claude, Google).
    """
    provider = (provider or "").lower()
    if provider.startswith("openai"):
        return OpenAIEngine(client)

    if provider.startswith("anthropic"):
        return AnthropicEngine(client)
    
    if provider.startswith("deepseek"):
        return DeepseekEngine(client)

    raise ValueError(f"Unsupported LLM provider: {provider}")
