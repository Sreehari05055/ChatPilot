from app.services.web.web_search_service import WebSearchService
from app.services.web.base_web_search_service import BaseWebSearchService
from app.services.web.tavily_search_service import TavilyWebSearchService
from app.core.config import Config
import httpx

class WebSearchProviderFactory:
    @staticmethod
    def get_provider(http_client: httpx.AsyncClient):

        if getattr(Config, 'TAVILY_API_KEY', None):
            return TavilyWebSearchService()

        if getattr(Config, 'WEB_SEARCH_API_KEY', None) and getattr(Config, 'CSE_ID', None):
            return WebSearchService(http_client=http_client)

        return BaseWebSearchService()