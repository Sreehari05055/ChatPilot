from app.core.config import Config


class BaseWebSearchService:
    async def run_web_search(self, query, num_results=Config.WEB_SEARCH_NUM_RESULTS) -> str:
        return "Web search is not available. Please find the configuration or the required API keys."

    