from app.services.rag_service.rag_key_functions import RAGPipeline
from app.services.rag_service.content_summarizer import RAGSummarizer
import asyncio
from app import logger

class RAGExecutionService:
    def __init__(self, llm_engine):
        self.rag_pipeline = RAGPipeline()
        self.rag_summarizer = RAGSummarizer(llm_engine)

    async def init_index(self):
        await self.rag_pipeline._build_index()

    async def get_info(self, query):
        logger.info(f"Fetching quick knowledge for query: {query}")
        context_list = await self.rag_pipeline._get_corpus_data(query)
        logger.info(f"Retrieved {context_list} context chunks.")
        formatted_context = "\n\n---\n\n".join(context_list)
        return formatted_context
    
    async def get_info_with_explanation(self, query):
        logger.info(f"Fetching summarized knowledge for query: {query}")
        knowledge = await self.rag_pipeline._get_corpus_data(query)
        formatted_knowledge = "\n\n---\n\n".join(knowledge)
        logger.info(f"Retrieved {formatted_knowledge} for summarization.")
        summarized_knowledge = await self.rag_summarizer.summarize(formatted_knowledge, query)
        return summarized_knowledge