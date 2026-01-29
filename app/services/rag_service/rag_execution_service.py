from app.services.rag_service.rag_key_functions import RAGPipeline
import asyncio
from app import logger

class RAGExecutionService:
    def __init__(self):
        self.rag_pipeline = RAGPipeline()

    async def init_index(self):
        """Initial load of the index (used on app startup)."""
        await self.rag_pipeline._load_index()

    async def rebuild_index(self):
        """Full wipe and rebuild of the index (used by Ingest API)."""
        await self.rag_pipeline._build_index()

    async def get_info(self, queries: list[str], user_query: str):
        logger.info(f"Fetching quick knowledge for keywords: {queries}")
        context_list = await self.rag_pipeline._get_corpus_data(queries, user_query)
        formatted_context = "\n\n".join([f"doc_id: {n['doc_id']} \nRELEVANCE TO QUESTION SCORE: {n['score']}\nCONTENT: \n {n['content']}" for n in context_list])
        logger.info(f"Retrieved {len(context_list)} context chunks from RAG index.")
        logger.debug(f"Context details: {formatted_context}")
        logger.info(f"User query: {user_query}")
        return formatted_context
