from app.core.config import Config
from app.services.scholar_research.base_research import BaseResearchService
from app.services.scholar_research.openalex_service import OpenAlexResearchService

class ResearchProviderFactory:
    @staticmethod
    def get_provider(http_client=None):

        if getattr(Config, 'OPENALEX_API_KEY', None):
            return OpenAlexResearchService(http_client=http_client)

        return BaseResearchService()