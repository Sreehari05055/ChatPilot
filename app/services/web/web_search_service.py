import httpx
from app import logger
from app.core.config import Config
from app.services.web.base_web_search_service import BaseWebSearchService

class WebSearchService(BaseWebSearchService):
    def __init__(self, http_client: httpx.AsyncClient):
        self.http_client = http_client

    async def run_web_search(self, query, num_results=Config.WEB_SEARCH_NUM_RESULTS, **kwargs) -> str:
        try:
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "q": query,
                "key": Config.WEB_SEARCH_API_KEY,
                "cx": Config.CSE_ID,
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
        
    async def web_fetch(self, url: str) -> str:
        """Fetch page using httpx and parse using WebContentParser."""
        try:
            from app.services.web.web_parser import WebContentParser
            response = await self.http_client.get(url, follow_redirects=True, timeout=Config.HTTP_TIMEOUT)
            content_type = response.headers.get('content-type', '').lower()
            
            return WebContentParser.parse_content(response.content if 'pdf' in content_type else response.text, content_type)
        except Exception as e:
            logger.error(f"Fetch failed for {url}: {e}", exc_info=True)
            return f"Fetch error: {str(e)}"

    async def web_research(self, query: str) -> str:
        """Standard search fallback for research."""
        try:
            logger.info(f"Performing standard web research for: {query}")
            results = await self.run_web_search(query, num_results=10)
            return f"RESEARCH REPORT (Standard Search):\n\n{results}\n\nNote: This is a standard search crawl. For agentic deep-research, please configure Tavily."
        except Exception as e:
            logger.error(f"Standard research failed: {e}", exc_info=True)
            return f"Research error: {str(e)}"
