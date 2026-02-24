import os
from app.services.rag_service.base_rag_pipeline import BaseRAGPipeline
from app.core.config import Config
from app import logger

class UnifiedRAGPipeline(BaseRAGPipeline):
    """
    Modular RAG Pipeline that assembles embedding models and rerankers
    based on the configuration providers.
    """
    
    def __init__(self):
        super().__init__()
        logger.info(f"Initializing Unified RAG Pipeline")
        logger.info(f"Embedding Provider: {Config.EMBEDDING_PROVIDER} ({Config.EMBEDDING_MODEL})")
        logger.info(f"Reranker Provider: {Config.RERANKER_PROVIDER} ({Config.RERANKING_MODEL})")
        
        self.doc_embed_model = self._setup_embedding(is_query=False)
        self.query_embed_model = self._setup_embedding(is_query=True)
        self.reranker = self._setup_reranker()

    def _setup_embedding(self, is_query=False):
        provider = Config.EMBEDDING_PROVIDER
        model_name = Config.EMBEDDING_MODEL
        
        if provider == "openai":
            from llama_index.embeddings.openai import OpenAIEmbedding
            api_key = os.getenv("OPENAI_API_KEY")
            return OpenAIEmbedding(
                api_key=api_key,
                model_name=model_name
            )
            
        elif provider == "cohere":
            from llama_index.embeddings.cohere import CohereEmbedding
            input_type = "search_query" if is_query else "search_document"
            return CohereEmbedding(
                api_key=Config.COHERE_API_KEY,
                model_name=model_name,
                input_type=input_type,
            )
            
        elif provider == "local":
            from llama_index.embeddings.huggingface import HuggingFaceEmbedding
            device = "cuda" if Config.USE_GPU_ACCELERATION else "cpu"
            return HuggingFaceEmbedding(
                model_name=model_name,
                device=device
            )
        
        elif provider == "ollama":
            from llama_index.embeddings.ollama import OllamaEmbedding
            return OllamaEmbedding(
                model_name=model_name,
                base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            )
        
        else:
            raise ValueError(f"Unsupported embedding provider: {provider}")

    def _setup_reranker(self):
        provider = Config.RERANKER_PROVIDER
        model_name = Config.RERANKING_MODEL
        
        if provider == "cohere":
            from llama_index.postprocessor.cohere_rerank import CohereRerank
            return CohereRerank(
                api_key=Config.COHERE_API_KEY,
                model=model_name,
                top_n=Config.TOP_N
            )
            
        elif provider == "local":
            from llama_index.postprocessor.flag_embedding_reranker import FlagEmbeddingReranker
            return FlagEmbeddingReranker(
                model=model_name,
                top_n=Config.TOP_N
            )
            
        elif provider == "none":
            return None
            
        else:
            logger.warning(f"Unsupported or no reranker provider: {provider}. Skipping reranking.")
            return None

    def get_doc_embed_model(self):
        return self.doc_embed_model
    
    def get_query_embed_model(self):
        return self.query_embed_model
    
    def get_reranker(self):
        return self.reranker
