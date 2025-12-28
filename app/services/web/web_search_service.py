from serpapi.google_search import GoogleSearch
import httpx
from app import logger
from app.core.config import Config
from app.services.web.base_web_search_service import BaseWebSearchService

class WebSearchService(BaseWebSearchService):
    def __init__(self, cse_id, web_search_api, http_client: httpx.AsyncClient):
        self.cse_id = cse_id
        self.web_search_api = web_search_api
        self.http_client = http_client

    async def run_web_search(self, query, num_results=Config.WEB_SEARCH_NUM_RESULTS) -> str:
        try:
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "q": query,
                "key": self.web_search_api,
                "cx": self.cse_id,
                "num": num_results,
                "engine": "google"
            }
            response = await self.http_client.get(url, params=params, timeout=Config.HTTP_TIMEOUT)
            results = response.json()
            
            # Check for errors in the response
            if "error" in results:
                logger.error(f"Web search error: {results['error']}")
                return f"Search error: {results['error']}"
            
            # Extract top organic results
            items = results.get("items", [])
            if not items:
                return "No search results found."
                
            formatted = []
            for r in items:
                title = r.get("title", "")
                snippet = r.get("snippet", "")
                link = r.get("link", "")
                formatted.append(f"Title: {title}\nSnippet: {snippet}\nLink: {link}")
                logger.info(f"Web search result - Title: {title}, Link: {link}")
            return "\n\n".join(formatted)
        except Exception as e:
            logger.error(f"Exception during web search: {e}", exc_info=True)
            return f"Search error: {str(e)}"
