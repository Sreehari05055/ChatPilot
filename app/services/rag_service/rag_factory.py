from app.services.rag_service.base_rag_pipeline import BaseRAGPipeline
from app.core.config import Config
from app import logger
from app.services.rag_service.cohere_rag_pipeline import CohereRAGPipeline
from app.services.rag_service.local_rag_pipeline import LocalRAGPipeline


class RAGProviderFactory:
    @staticmethod
    def get_provider():

        if getattr(Config, 'COHERE_API_KEY', None):
            return CohereRAGPipeline()
        return LocalRAGPipeline()