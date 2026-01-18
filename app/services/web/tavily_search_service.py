import httpx
from app import logger
from app.core.config import Config
from app.services.web.base_web_search_service import BaseWebSearchService
from tavily import TavilyClient
from datetime import datetime

class TavilyWebSearchService(BaseWebSearchService):
    def __init__(self):
        self.tavily_client = TavilyClient(api_key=Config.TAVILY_API_KEY)

    async def run_web_search(self, query, num_results=Config.WEB_SEARCH_NUM_RESULTS, topic="general", time_range=None, start_date: str = None, end_date: str = None) -> str:
        try:
            response = self.tavily_client.search(
                query=query, 
                topic=topic,
                max_results=num_results,
                search_depth="advanced",
                time_range=time_range,
                start_date=start_date,
                end_date=end_date
            )
            
            if "results" not in response:
                logger.error(f"Tavily search error: {response}")
                return "No search results found."
            
            formatted = []
            for r in response["results"]:
                title = r.get("title", "")
                content = r.get("content", "")
                url = r.get("url", "")
                formatted.append(f"Title: {title}\nContent: {content}\nLink: {url}")
            return "\n\n".join(formatted)
        except Exception as e:
            logger.error(f"Tavily search failed: {e}", exc_info=True)
            return f"Search error: {str(e)}"

    async def web_fetch(self, url: str) -> str:
        """Use Tavily Extract API to get clean content."""
        try:
            response = self.tavily_client.extract(
                urls=[url],
                max_results=Config.WEB_SEARCH_NUM_RESULTS,
                extract_depth="advanced",
                chunks_per_source=4,
                format="text"
            )
            
            if "results" not in response:
                logger.error(f"Tavily extract error: {response}")
                return "No content could be extracted from the provided URL."
       
            formatted = []
            for r in response["results"]:
                title = r.get("title", "")
                content = r.get("content", "")
                url = r.get("url", "")
                formatted.append(f"Title: {title}\nContent: {content}\nLink: {url}")
            return "\n\n".join(formatted)

        except Exception as e:
            logger.error(f"Tavily extract failed for {url}: {e}", exc_info=True)
            return f"Fetch error: {str(e)}"

    async def web_research(self, query: str) -> str:
        try:
            # Tavily research returns a structured report and sources.
            response = self.tavily_client.research(
                query=query,
                model="mini"
            )
            
            content = response.get("content", "")
            sources = response.get("sources", [])
            
            if not content:
                logger.error(f"Tavily research error: {response}")
                return "No research content found."
            
            formatted_sources = []
            for s in sources:
                title = s.get("title", "Unknown Source")
                url = s.get("url", "")
                formatted_sources.append(f"- {title}: {url}")
            
            sources_str = "\n".join(formatted_sources)
            return f"RESEARCH REPORT:\n\n{content}\n\nSOURCES:\n{sources_str}"

        except Exception as e:
            logger.error(f"Tavily research failed: {e}", exc_info=True)
            return f"Research error: {str(e)}"