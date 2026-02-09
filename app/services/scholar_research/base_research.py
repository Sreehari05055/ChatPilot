from app.core.config import Config


class BaseResearchService:
    async def semantic_scholar_search(self, query, count=25, publication_year=None, is_open_access=None, has_pdf=None) -> str:
        return "Semantic Scholar search functionality is not available. Please check your configuration."


    async def _research_articles(self, query, MAX_RESULTS=Config.WEB_SEARCH_NUM_RESULTS) -> str:
        return "Scholar research functionality is not available. Please check your configuration."
    async def _retrieve_articles(self, query, **kwargs) -> str:
        return "Article retrieval functionality is not available. Please check your configuration."
    async def _index_articles(self, articles, **kwargs) -> str:
        return "Article indexing functionality is not available. Please check your configuration."
    async def _respond_with_articles(self, query, **kwargs) -> str:
        return "Article response generation is not available. Please check your configuration."

