from app.core import config
from typing import Optional, AsyncGenerator, Any
from app.services.llm_engine.base_gpt_engine import LLMEngine
from app.services.llm_engine.tool_definitions import OPENAI_TOOLS
from app import logger

class OpenAIEngine(LLMEngine):
    def __init__(self, client):
        self.client = client
        self.tools = OPENAI_TOOLS

    async def _gpt_engine_stream(self, messages: list, model: str,
                                  top_p: float, max_completion_tokens: int, temperature: float,
                                  stream: bool = True, **kwargs) -> Optional[AsyncGenerator[Any, None]]:
        system_str = kwargs.get("system_prompt", "")
        use_tools = kwargs.get("use_tools", True)  # Allow disabling tools
        try:
            combined_messages = [{"role": "system", "content": system_str}] + messages

            create_params = {
                "model": model,
                "messages": combined_messages,
                "top_p": top_p,
                "max_completion_tokens": max_completion_tokens,
                "temperature": temperature,
                "stream": stream,
            }
            
            if use_tools:
                create_params["tools"] = self.tools

            response = await self.client.chat.completions.create(**create_params)
            return response
        except Exception as e:
            logger.error(f"Error in OpenAIEngine _gpt_engine_stream: {str(e)}", exc_info=True)
            raise

    async def stream_response(self, messages: list, model: str,
                              top_p: float, max_completion_tokens: int, temperature: float,
                               stream: bool = True, **kwargs):
        """Unified async iterator that yields normalized chunks for streaming consumers.

        Chunk format: {"type": "delta"|"function_call"|"end"|"error", "content": str|None, "function": dict|None}
        """
        sys_prompt = kwargs.get("system_prompt", "")

        provider_stream = await self._gpt_engine_stream(
            messages, model, top_p, max_completion_tokens, temperature, stream=stream, system_prompt=sys_prompt
        )

        async for provider_chunk in provider_stream:
            try:
                if not provider_chunk.choices:
                    continue
                delta = provider_chunk.choices[0].delta
                content = getattr(delta, "content", None)
                tool_calls = getattr(delta, "tool_calls", None)

                if tool_calls:
                    for tc in tool_calls:
                        yield {
                            "type": "function_call", 
                            "content": None, 
                            "function": {
                                "id": getattr(tc, "id", None),  # Include tool call ID
                                "name": getattr(tc.function, "name", None),
                                "arguments_fragment": getattr(tc.function, "arguments", None)
                            }
                        }
                elif content:
                    yield {"type": "delta", "content": content, "function": None}
            except Exception:
                continue
        yield {"type": "end", "content": None, "function": None}
