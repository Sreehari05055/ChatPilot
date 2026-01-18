from app.core.config import Config


class BaseWebSearchService:
    async def run_web_search(self, query, num_results=Config.WEB_SEARCH_NUM_RESULTS, **kwargs) -> str:
        return "Web search is not available. Please find the configuration or the required API keys."

    async def web_fetch(self, url: str) -> str:
        return "Web fetching is not available. Please check your configuration."

    async def web_research(self, query: str) -> str:
        return "Web research is not available. Please check your configuration."