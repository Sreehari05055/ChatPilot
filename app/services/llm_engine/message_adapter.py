"""
Message format adapters for different LLM providers.
Converts between unified internal format and provider-specific formats.
"""
from typing import List, Dict, Any
from abc import ABC, abstractmethod


class MessageAdapter(ABC):
    """Base adapter for converting message formats"""
    
    @abstractmethod
    def to_provider_format(self, messages: List[Dict]) -> List[Dict]:
        """Convert internal format to provider format"""
        pass
    
    @abstractmethod
    def get_tool_result_key(self) -> str:
        """Get the key name for tool results (tool_call_id vs tool_use_id)"""
        pass


class OpenAIMessageAdapter(MessageAdapter):
    """Adapter for OpenAI message format"""
    
    def to_provider_format(self, messages: List[Dict]) -> List[Dict]:
        """OpenAI accepts messages as-is, including system messages"""
        return messages
    
    def get_tool_result_key(self) -> str:
        return "tool_call_id"


class AnthropicMessageAdapter(MessageAdapter):
    """Adapter for Anthropic message format"""
    
    def to_provider_format(self, messages: List[Dict]) -> List[Dict]:
        """
        Anthropic-specific transformations:
        1. Remove system messages (handled separately)
        2. Convert tool_call_id to tool_use_id
        3. Ensure alternating user/assistant pattern
        """
        converted = []
        
        for msg in messages:
            role = msg.get("role")
            
            # Skip system messages - Anthropic handles these separately
            if role == "system":
                continue
            
            # Convert tool messages to Anthropic format
            if role == "tool":
                # Support both tool_call_id (OpenAI) and tool_use_id (Anthropic) from history
                tool_id = msg.get("tool_call_id") or msg.get("tool_use_id")
                
                # Skip tool messages without valid IDs
                if not tool_id:
                    from app import logger
                    logger.warning(f"⚠️ Skipping tool message without valid ID: {msg.get('name')}")
                    continue
                
                from app import logger
                logger.debug(f"Converting tool message with ID: {tool_id}")
                    
                converted.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": msg.get("content", "")
                    }]
                })
            
            # Convert assistant messages with tool calls
            elif role == "assistant" and msg.get("tool_calls"):
                content_blocks = []
                
                # Add text content if present
                if msg.get("content"):
                    content_blocks.append({
                        "type": "text",
                        "text": msg["content"]
                    })
                
                # Add tool use blocks
                for tool_call in msg["tool_calls"]:
                    content_blocks.append({
                        "type": "tool_use",
                        "id": tool_call["id"],
                        "name": tool_call["function"]["name"],
                        "input": self._parse_arguments(tool_call["function"]["arguments"])
                    })
                
                converted.append({
                    "role": "assistant",
                    "content": content_blocks
                })
            
            # Regular user/assistant messages
            else:
                converted.append(msg)
        
        return converted
    
    def _parse_arguments(self, args_str: str) -> Dict:
        """Parse function arguments string to dict"""
        import json
        try:
            if not args_str or not args_str.strip():
                return {}
            parsed = json.loads(args_str)
            
            # Remove null values that Anthropic doesn't like
            return {k: v for k, v in parsed.items() if v is not None}
        except:
            return {}
    
    def get_tool_result_key(self) -> str:
        return "tool_use_id"


class DeepSeekMessageAdapter(OpenAIMessageAdapter):
    """DeepSeek uses OpenAI-compatible format"""
    pass


def get_message_adapter(provider: str) -> MessageAdapter:
    """Factory function to get appropriate adapter"""
    adapters = {
        "openai": OpenAIMessageAdapter(),
        "anthropic": AnthropicMessageAdapter(),
        "deepseek": DeepSeekMessageAdapter(),
    }
    return adapters.get(provider.lower(), OpenAIMessageAdapter())
