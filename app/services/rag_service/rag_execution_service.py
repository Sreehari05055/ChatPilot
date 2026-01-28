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
        
        formatted_context = "\n\n".join(
            [f"{item['content']}" for item in context_list]
        )
        logger.info(f"User query for RAG retrieval: {user_query}")
        logger.info(f"Retrieved {formatted_context} from RAG.")
        return formatted_context