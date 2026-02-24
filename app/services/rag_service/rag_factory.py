from app.services.rag_service.unified_rag_pipeline import UnifiedRAGPipeline

class RAGProviderFactory:
    @staticmethod
    def get_provider():
        return UnifiedRAGPipeline()