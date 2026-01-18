from app.services.rag_service.rag_key_functions import RAGPipeline
from app.services.rag_service.content_summarizer import RAGSummarizer
import asyncio
from app import logger

class RAGExecutionService:
    def __init__(self):
        self.rag_pipeline = RAGPipeline()
        self.rag_summarizer = RAGSummarizer()

    async def init_index(self):
        await self.rag_pipeline._build_index()

    async def get_info(self, query):
        logger.info(f"Fetching quick knowledge for query: {query}")
        context_list = await self.rag_pipeline._get_corpus_data(query)
        logger.info(f"Retrieved {context_list} context chunks.")
        formatted_context = "\n\n---\n\n".join(context_list)
        return formatted_context
    
    async def get_info_with_explanation(self, queries:list[str]):
        logger.info(f"Fetching summarized knowledge for query: {queries}")
        knowledge = await self.rag_pipeline._get_corpus_data(queries)
        formatted_knowledge = "\n\n---\n\n".join("\n\n---\n\n".join(k) for k in knowledge)
        logger.info(f"Retrieved {formatted_knowledge} for summarization.")
        summarized_knowledge = await self.rag_summarizer.summarize(formatted_knowledge, queries)
        return summarized_knowledge