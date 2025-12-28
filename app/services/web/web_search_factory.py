from app.services.web.web_search_service import WebSearchService
from app.services.web.base_web_search_service import BaseWebSearchService

class WebSearchProviderFactory:
    @staticmethod
    def get_provider(config, http_client=None):

        enabled = getattr(config, 'WEB_SEARCH_ENABLED', False)
      
        if isinstance(enabled, str):
            enabled = enabled.lower() in ("1", "true", "yes", "on")
        if not enabled:
            return BaseWebSearchService()

        if getattr(config, 'WEB_SEARCH_API_KEY', None) and getattr(config, 'CSE_ID', None):
            return WebSearchService(config.CSE_ID, config.WEB_SEARCH_API_KEY, http_client)

        return BaseWebSearchService()
