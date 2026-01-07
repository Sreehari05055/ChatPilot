import json
from typing import Any, AsyncGenerator, Optional
from app.services.llm_engine.base_gpt_engine import LLMEngine
from app.services.llm_engine.tool_definitions import ANTHROPIC_TOOLS
from app.services.llm_engine.message_adapter import AnthropicMessageAdapter
from app import logger

class AnthropicEngine(LLMEngine):
    """Anthropic LLM Engine implementation."""

    def __init__(self, client):
        self.client = client
        self.functions = ANTHROPIC_TOOLS
        self.adapter = AnthropicMessageAdapter()
    
    async def _gpt_engine_stream(self, messages: list, model: str,
                                  top_p: float, max_completion_tokens: int, temperature: float,
                                  stream: bool = True, **kwargs) -> Optional[AsyncGenerator[Any, None]]:
        use_tools = kwargs.get("use_tools", True)  # Allow disabling tools
        try:
            # Convert messages to Anthropic format
            anthropic_messages = self.adapter.to_provider_format(messages)
            
            create_params = {
                "model": model,
                "messages": anthropic_messages,
                "system": kwargs.get("system_prompt", ""),
                "max_tokens": max_completion_tokens,
                "temperature": temperature,
                "stream": stream,
            }
            
            if use_tools:
                create_params["tools"] = self.functions

            response = await self.client.messages.create(**create_params)
            return response
        except Exception as e:
            logger.error(f"Error in AnthropicEngine _gpt_engine_stream: {str(e)}", exc_info=True)
            # Return error generator instead of None
            async def error_gen():
                yield {"type": "error", "content": f"Anthropic API error: {str(e)}", "function": None}
            return error_gen()
    


    async def stream_response(self, messages: list, model: str,
                    top_p: float, max_completion_tokens: int, temperature: float,
                    stream: bool = True , **kwargs):
        """Unified async iterator that yields normalized chunks for streaming consumers.
        Chunk format: {"type": "delta"|"function_call"|"end"|"error", "content": str|None, "function": dict|None}
        """
        sys_prompt = kwargs.get("system_prompt", "")
        provider_stream = await self._gpt_engine_stream(
                    messages, model, top_p, max_completion_tokens, temperature, stream=stream, system_prompt=sys_prompt
                )

        async for provider_chunk in provider_stream:
            try:
                # Anthropic Streaming Events
                ctype = getattr(provider_chunk, "type", None)

                # 1. Handle Text Content
                if ctype == "content_block_delta" and provider_chunk.delta.type == "text_delta":
                    content = provider_chunk.delta.text
                    yield {"type": "delta", "content": content, "function": None}

                # 2. Handle Tool Use (Function Call) Start
                elif ctype == "content_block_start" and provider_chunk.content_block.type == "tool_use":
                    yield {
                        "type": "function_call", 
                        "content": None, 
                        "function": {
                            "name": provider_chunk.content_block.name,
                            "id": provider_chunk.content_block.id,
                            "arguments_fragment": ""
                        }
                    }
                # 3. Handle Tool Use (Function Call) JSON Fragments
                elif ctype == "content_block_delta" and provider_chunk.delta.type == "input_json_delta":
                    yield {
                        "type": "function_call", 
                        "content": None, 
                        "function": {
                            "name": None,
                            "id": None,  # ID already sent in content_block_start
                            "arguments_fragment": provider_chunk.delta.partial_json
                        }
                    }
                elif ctype == "content_block_delta" and provider_chunk.delta.type == "thinking_delta":
                    continue

            except Exception:
                continue
        yield {"type": "end", "content": None, "function": None}