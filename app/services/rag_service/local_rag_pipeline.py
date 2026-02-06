from app.services.rag_service.base_rag_pipeline import BaseRAGPipeline
from app.core.config import Config
from app import logger

class LocalRAGPipeline(BaseRAGPipeline):
    """
    RAG Pipeline using local HuggingFace models for embeddings and reranking.
    No API keys required - runs entirely on local hardware.
    """
    
    def __init__(self):
        super().__init__()
        logger.info("Initializing Local (HuggingFace) RAG Pipeline")
        
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding
        from llama_index.postprocessor.flag_embedding_reranker import FlagEmbeddingReranker

        # Use Jina v2 for embeddings
        embedding_model_name = getattr(Config, "EMBEDDING_MODEL", "BAAI/bge-m3-small-v1.5")  # Default to a smaller model for local use
        
        # Configure device based on GPU acceleration flag
        device = "cuda" if Config.USE_GPU_ACCELERATION else "cpu"
        
        self.embed_model = HuggingFaceEmbedding(
            model_name=embedding_model_name,
            device=device,
        )
        
        logger.info(f"Using device: {device}")
        
        # Local cross-encoder reranker
        self.reranker = FlagEmbeddingReranker(
            model=getattr(Config, "RERANKING_MODEL", "BAAI/bge-reranker-v2-m3"),
            top_n=getattr(Config, "TOP_N", 10)
        )
        
        logger.info(f"Using local embedding model: {embedding_model_name}")
        logger.info(f"Using local reranker: {getattr(Config, 'RERANKING_MODEL', 'BAAI/bge-reranker-v2-m3')}")
    
    def get_doc_embed_model(self):
        return self.embed_model
    
    def get_query_embed_model(self):
        # Local models use the same embedding for both
        return self.embed_model
    
    def get_reranker(self):
        return self.reranker
