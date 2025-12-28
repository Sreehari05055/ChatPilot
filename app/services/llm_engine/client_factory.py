from typing import Any, Optional
import openai
import asyncio
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from app.core.config import Config


def build_llm_client(provider: Optional[str], config: Config) -> Any:
    """Create a provider-specific low-level client based on config.

    Returns a client instance appropriate for the provider, or None if
    the provider expects the engine to construct its own client.
    """
    provider = (provider or "").lower().strip()

    if provider.startswith("openai"):
        return openai.AsyncOpenAI(api_key=config.LLM_API_KEY)
    
    if provider.startswith("deepseek"):
        return AsyncOpenAI(api_key=config.LLM_API_KEY, base_url="https://api.deepseek.com")
    
    if provider.startswith("anthropic"):
        return AsyncAnthropic(api_key=config.LLM_API_KEY)
    
    return None
