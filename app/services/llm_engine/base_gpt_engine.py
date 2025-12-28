from abc import ABC, abstractmethod
from typing import Optional, AsyncGenerator, Any

class LLMEngine(ABC):
    """Abstract base class for LLM providers.

    Provide two entry points:
      - `_gpt_engine_stream(...)` returns an async generator for streaming responses
      - `_gpt_engine(...)` returns a non-streaming response object
    """

    @abstractmethod
    async def _gpt_engine_stream(self, messages: list, model: str,
                                 top_p: float, max_completion_tokens: int, temperature: float, stream: bool, **kwargs) -> Optional[AsyncGenerator[Any, None]]:
        raise NotImplementedError()
    
    @abstractmethod
    async def stream_response(self, messages: list, model: str,
                              top_p: float, max_completion_tokens: int, temperature: float, stream: bool, **kwargs):
        raise NotImplementedError()