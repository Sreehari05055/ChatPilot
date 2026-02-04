from app.services.rag_service.base_rag_pipeline import BaseRAGPipeline
from app.core.config import Config
from app import logger


class CohereRAGPipeline(BaseRAGPipeline):
    """
    RAG Pipeline using Cohere for embeddings and reranking.
    Requires COHERE_API_KEY in environment.
    """
    
    def __init__(self):
        super().__init__()
        logger.info("Initializing Cohere RAG Pipeline")
        
        from llama_index.embeddings.cohere import CohereEmbedding
        from llama_index.postprocessor.cohere_rerank import CohereRerank
        
        # Document embeddings (for indexing)
        self.doc_embed_model = CohereEmbedding(
            api_key=Config.COHERE_API_KEY,
            model_name="embed-english-v3.0",
            input_type="search_document",
            embedding_type="float",
        )

        # Query embeddings (for retrieval)
        self.query_embed_model = CohereEmbedding(
            api_key=Config.COHERE_API_KEY,
            model_name="embed-english-v3.0",
            input_type="search_query",
            embedding_type="float",
        )

        # High-precision reranker
        self.reranker = CohereRerank(
            api_key=Config.COHERE_API_KEY,
            model="rerank-english-v3.0",
            top_n=getattr(Config, "TOP_N", 10)
        )
    
    def get_doc_embed_model(self):
        return self.doc_embed_model
    
    def get_query_embed_model(self):
        return self.query_embed_model
    
    def get_reranker(self):
        return self.reranker
