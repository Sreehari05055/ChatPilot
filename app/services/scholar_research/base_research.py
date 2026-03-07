from app.core.config import Config


class BaseResearchService:
    async def semantic_scholar_search(self, query, count=10, publication_year=None, is_oa=None, has_pdf=None) -> str:
        return "Semantic Scholar search functionality is not available. Please check your configuration."

