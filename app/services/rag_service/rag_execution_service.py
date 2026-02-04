
import asyncio
from app import logger

from app.services.rag_service.rag_factory import RAGProviderFactory

class RAGExecutionService:
    def __init__(self, pipeline=None):
        self.rag_pipeline = pipeline or RAGProviderFactory.get_provider()

    async def init_index(self):
        """Initial load of the index (used on app startup)."""
        await self.rag_pipeline._load_index()

    async def rebuild_index(self):
        """Full wipe and rebuild of the index (used by Ingest API)."""
        await self.rag_pipeline._build_index()

    async def get_info(self, queries: list[str], user_query: str):
        logger.info(f"Fetching quick knowledge for keywords: {queries}")
        context_list = await self.rag_pipeline._get_corpus_data(queries, user_query)
        
        # 1. Format for the LLM (internal reasoning) - Including Score for relevance check
        formatted_context = "\n\n".join([
            f"SOURCE: {n['doc_id']} (Page {n.get('page_label', 'N/A')})\n"
            f"RELEVANCE SCORE: {n.get('score', 0.0):.4f}\n"
            f"CONTENT: {n['content']}" 
            for n in context_list
        ])
        
        logger.info(f"Retrieved {len(context_list)} context chunks from RAG index.")
        logger.debug(f"Context details: {formatted_context}")
        
        # 2. Return BOTH the string for the LLM and the structured data for the frontend
        return {
            "context_text": formatted_context,
            "sources": context_list
        }
