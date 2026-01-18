from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from app.core.config import Config

config = Config()

class LangChainService:
    @staticmethod
    def get_llm(provider: str = None, model_name: str = None) -> BaseChatModel:
        """
        Factory to get the appropriate LangChain chat model based on provider.
        """
        provider = provider or config.LLM_PROVIDER
        model_name = model_name or config.MODEL_NAME
        api_key = config.LLM_API_KEY
        
        # Consistent settings
        kwargs = {
            "model": model_name,
            "temperature": config.TEMPERATURE,
            "max_tokens": config.MAX_TOKENS,
        }

        if provider == "openai":
            return ChatOpenAI(
                api_key=api_key,
                top_p=config.TOP_P,
                **kwargs
            )
        
        elif provider == "anthropic":
            # Adapt params for Anthropic if needed (e.g. max_tokens_to_sample)
            # ChatAnthropic uses 'max_tokens' now
            return ChatAnthropic(
                api_key=api_key,
                **kwargs
            )
            
        elif provider == "deepseek":
            # DeepSeek is OpenAI compatible
            return ChatOpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com/v1",
                top_p=config.TOP_P,
                **kwargs
            )
            
        else:
            raise ValueError(f"Unsupported provider: {provider}")
