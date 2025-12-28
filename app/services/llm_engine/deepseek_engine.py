from typing import Any, AsyncGenerator, Optional
from app.services.llm_engine.base_gpt_engine import LLMEngine
from app import logger

class DeepseekEngine(LLMEngine):
    def __init__(self, client):
        self.client = client
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Rephrase the user's question to do a web search to find relevant information.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "The user's question to be rephrased and web searched."
                            }
                        },
                        "required": ["question"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "web_fetch",
                    "description": "Fetch and analyze the content of a specific URL provided by the user.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "format": "uri",
                                "description": "The exact URL to fetch content from."
                            }
                        },
                        "required": ["url"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_data",
                    "description": "Use when the user asks to analyze provided data or files using code.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "TODO": {
                                "type": "string",
                                "description": "A clear description of the analysis task to perform."
                            }
                        },
                        "required": ["TODO"]
                    }
                }
            }
            
        ] 

    async def _gpt_engine_stream(self, messages: list, model: str,
                                  top_p: float, max_completion_tokens: int, temperature: float,
                                  stream: bool = True, **kwargs) -> Optional[AsyncGenerator[Any, None]]:
        system_str = kwargs.get("system_prompt", "")
        try:
            combined_messages = [{"role": "system", "content": system_str}] + messages

            response = await self.client.chat.completions.create(
                model=model,
                messages=combined_messages,
                tools = self.tools,
                top_p=top_p,
                max_tokens=max_completion_tokens,
                temperature=temperature,
                stream=stream,
            )
            return response
        except Exception as e:
            logger.error(f"Error in DeepseekEngine _gpt_engine_stream: {str(e)}", exc_info=True)
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
                                "name": getattr(tc.function, "name", None),
                                "arguments_fragment": getattr(tc.function, "arguments", None)
                            }
                        }
                elif content:
                    yield {"type": "delta", "content": content, "function": None}
            except Exception:
                continue
        yield {"type": "end", "content": None, "function": None}