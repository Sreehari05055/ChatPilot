from app.services.rag_service.rag_key_functions import RAGPipeline
import asyncio
from app import logger

class RAGExecutionService:
    def __init__(self):
        self.rag_pipeline = RAGPipeline()

    async def init_index(self):
        await self.rag_pipeline._build_index()

    async def get_info(self, queries: list[str]):
        logger.info(f"Fetching quick knowledge for query: {queries}")
        context_list = await self.rag_pipeline._get_corpus_data(queries)
        formatted_knowledge = "\n\n---\n\n".join("\n\n---\n\n".join(k) for k in context_list)
        logger.info(f"Retrieved {formatted_knowledge} for summarization.")
        return formatted_knowledge