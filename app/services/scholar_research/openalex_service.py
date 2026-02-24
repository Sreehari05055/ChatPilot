import httpx
from app.core.config import Config
from app.services.scholar_research.base_research import BaseResearchService
import requests

from app import logger

class OpenAlexResearchService(BaseResearchService):
    def __init__(self, http_client=None):
        self.api_key = Config.OPENALEX_API_KEY
        self.http_client = http_client
        self.works_url = "https://api.openalex.org/works" 


    async def semantic_scholar_search(self, query, count=25, publication_year=">1900", is_oa=True, has_pdf=True) -> list:
        params = {
            "search": query,
            "per-page": min(count, 200),
            "filter": f"publication_year:{publication_year},is_oa:{str(is_oa).lower()},has_pdf_url:{str(has_pdf).lower()}"
        }
        headers = {
            "User-Agent": "ResearchApp/1.0"  
        }
        if self.http_client is not None:
            client = self.http_client
            response = await client.get(self.works_url, params=params, headers=headers)
        else:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.works_url, params=params, headers=headers)
        
        results = response.json()["results"] if response.status_code == 200 else []
        
        if response.status_code != 200:
            logger.error(f"OpenAlex API error: {response.status_code} - {response.text}")
            return f"Error fetching research from OpenAlex: {response.status_code}"
        
        logger.info(f"OpenAlex returned results: {results}\n")
        
        formatted_results = []
        for item in results:
            pdf_url = None
            if item.get("open_access", {}).get("oa_url"):
                pdf_url = item["open_access"]["oa_url"]
            elif item.get("primary_location", {}).get("pdf_url"):
                pdf_url = item["primary_location"]["pdf_url"]

            # Extract work ID from full OpenAlex ID (e.g., https://openalex.org/W2741809807 -> W2741809807)
            work_id = item.get("id", "").split("/")[-1]

            formatted_results.append({
                "id": work_id,
                "title": item.get("title"),
                "authors": [author['author']['display_name'] for author in item.get("authorships", [])],
                "publication_year": item.get("publication_year"),
                "doi": item.get("doi"),
                "is_open_access": item.get("open_access", {}).get("is_oa"),
                "pdf_url": pdf_url,
                "landing_page_url": item.get("primary_location", {}).get("landing_page_url")
            })

        return formatted_results

    async def get_formatted_search_results(self, query, **kwargs) -> str:
        results = await self.semantic_scholar_search(query, **kwargs)
        if isinstance(results, str):
            return results
        return '\n\n'.join([f"Title: {r['title']}\nAuthors: {', '.join(r['authors'])}\nYear: {r['publication_year']}\nDOI: {r['doi']}\nOpen Access: {r['is_open_access']}\nPDF URL: {r['pdf_url']}\nLanding Page: {r['landing_page_url']}" for r in results])