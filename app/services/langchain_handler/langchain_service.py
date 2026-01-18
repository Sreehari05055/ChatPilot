from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from app.core.config import Config
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama

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
        
        # Shared settings
        temperature = config.TEMPERATURE
        max_tokens = config.MAX_TOKENS

        if provider == "openai":
            return ChatOpenAI(
                model=model_name,
                api_key=api_key,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=config.TOP_P
            )
        
        elif provider == "anthropic":
            return ChatAnthropic(
                model=model_name,
                api_key=api_key,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
        elif provider == "deepseek":
            return ChatOpenAI(
                model=model_name,
                api_key=api_key,
                base_url="https://api.deepseek.com/v1",
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=config.TOP_P
            )
        elif provider == "google":
            return ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=api_key,
                temperature=temperature,
                max_output_tokens=max_tokens
            )
        elif provider == "ollama":
            return ChatOllama(
                model=model_name,
                temperature=temperature
            )
        else:
            raise ValueError(f"Unsupported provider: {provider}")
