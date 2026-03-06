import os
import httpx
from typing import TypedDict, Annotated, List, Optional ,Union, Dict
from langgraph.graph import StateGraph, END
from app.core.config import Config
from app import logger
import operator
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage, BaseMessage
from app.services.scholar_research.factory import ResearchProviderFactory
from app.services.rag_service.rag_execution_service import RAGExecutionService
import asyncio

class ResearchState(TypedDict):
    original_query: str
    search_query: str
    sub_queries: List[str]
    count: int
    paper_metadata: List[dict]
    downloaded_files: List[str]
    report: str
    sources: List[dict]
    messages: Annotated[List[BaseMessage], operator.add]

class DeepScholarResearchService:
    def __init__(self, research_provider=None, rag_service=None):
        self.research_service = research_provider or ResearchProviderFactory.get_provider()
        self.rag_service = rag_service or RAGExecutionService()
        self.data_dir = Config.DATA_DIR
        self.api_key = Config.OPENALEX_API_KEY
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.workflow = self._create_workflow()
        
    def _route_entry(self, state: ResearchState) -> str:
        """Route to search or skip directly to download based on pre-filled paper_metadata."""
        if state.get("paper_metadata"):
            logger.info(f"Paper metadata pre-filled ({len(state['paper_metadata'])} papers). Skipping search.")
            return "download_papers"
        return "search_papers"
    
    def _create_workflow(self):
        workflow = StateGraph(ResearchState)

        workflow.add_node("router", lambda state: {})
        workflow.add_node("search_papers", self.search_papers)
        workflow.add_node("download_papers", self.download_papers)
        workflow.add_node("index_papers", self.index_papers)
        workflow.add_node("generate_report", self.generate_report)
        

        workflow.set_entry_point("router")
        workflow.add_conditional_edges("router", self._route_entry, {
            "search_papers": "search_papers",
            "download_papers": "download_papers"
        })
        workflow.add_edge("search_papers", "download_papers")
        workflow.add_edge("download_papers", "index_papers")
        workflow.add_edge("index_papers", "generate_report")
        workflow.add_edge("generate_report", END)
        
        return workflow.compile()

    async def search_papers(self, state: ResearchState):
        logger.info(f"Searching papers for: {state['search_query']} (Original: {state['original_query']})")
        results = await self.research_service.semantic_scholar_search(state['search_query'], count=state['count'])
        
        # If results is a string (error), handle it
        if isinstance(results, str):
            logger.error(f"Search failed: {results}")
            return {"paper_metadata": [], "messages": [AIMessage(content=f"Search failed: {results}")]}
            
        return {"paper_metadata": results}

    async def download_papers(self, state: ResearchState):
        downloaded = []

        async with httpx.AsyncClient(timeout=Config.HTTP_TIMEOUT) as client:
            for paper in state['paper_metadata']:
                work_id = paper.get("id")
                # Prioritize OpenAlex Content API for more reliable downloads
                if work_id:
                    pdf_url = f"https://content.openalex.org/works/{work_id}.pdf"
                    if self.api_key:
                        pdf_url += f"?api_key={self.api_key}"
                else:
                    pdf_url = paper.get("pdf_url")
                
                if not pdf_url:
                    continue
                
                try:
                    # Create a safe filename
                    filename = "".join([c if c.isalnum() else "_" for c in paper['title'][:50]]) + ".pdf"
                    filepath = os.path.join(self.data_dir, filename)
                    
                    # Skip if file already exists on disk
                    if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                        logger.info(f"Skipping already downloaded: {filename}")
                        downloaded.append(filepath)
                        continue

                    logger.info(f"Downloading {paper['title']} from {pdf_url}")
                    # Standard User-Agent set in headers
                    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
                    response = await client.get(pdf_url, headers=headers, follow_redirects=True)
                    
                    if response.status_code == 200:
                        content = response.content
                        if not content.startswith(b"%PDF-"):
                            logger.warning(
                                f"Response is not a valid PDF for {paper['title']} "
                                f"(Content-Type: {response.headers.get('Content-Type')})"
                            )
                            continue

                        with open(filepath, "wb") as f:
                            f.write(content)
                        downloaded.append(filepath)
                        logger.info(f"Successfully downloaded: {filename}")
                    else:
                        logger.warning(f"Failed to download {paper['title']}: {response.status_code}")
                except Exception as e:
                    logger.error(f"Error downloading {paper['title']}: {e}")
        
        return {"downloaded_files": downloaded}

    async def index_papers(self, state: ResearchState):
        if not state['downloaded_files']:
            logger.warning("No papers downloaded to index.")
            return {}
        
        logger.info("Rebuilding RAG index with new papers...")
        await self.rag_service.rebuild_index()
        return {}

    async def generate_report(self, state: ResearchState):
        logger.info(f"Generating report for: {state['original_query']}")
        
        # Perform RAG retrieval using sub_queries
        rag_results = await self.rag_service.get_info(state['sub_queries'], state['original_query'])
        context = rag_results.get("context_text", "No relevant context found.")
        sources = rag_results.get("sources", [])
        
        downloaded_titles = set()
        for f in state.get('downloaded_files', []):
            downloaded_titles.add(os.path.basename(f))
        

        report = f"Research Report for: {state['original_query']}\n\n"
        report += "Papers Successfully Downloaded & Indexed:\n"
        for paper in state['paper_metadata']:
            filename = "".join([c if c.isalnum() else "_" for c in paper['title'][:50]]) + ".pdf"
            if filename in downloaded_titles:
                report += f"- {paper['title']} ({paper['publication_year']})\n"
                
        failed = [p for p in state['paper_metadata']
            if "".join([c if c.isalnum() else "_" for c in p['title'][:50]]) + ".pdf" not in downloaded_titles]
        if failed:
            report += "\nPapers That Could NOT Be Downloaded (unavailable PDFs — do NOT retry):\n"
            for paper in failed:
                report += f"- {paper['title']} ({paper['publication_year']})\n"
        
        report += "\nKey Insights from Documents:\n"
        report += context
        
        return {"report": report, "sources": sources}

    async def run_research(self, original_query: str, sub_queries: List[str], search_query: Optional[str] = None, paper_metadata: Optional[List[dict]] = None,count: int = 5):
        initial_state = {
            "original_query": original_query,
            "search_query": search_query or "",
            "sub_queries": sub_queries,
            "count": count,
            "paper_metadata": paper_metadata or [],
            "downloaded_files": [],
            "report": "",
            "sources": [],
            "messages": [HumanMessage(content=original_query)]
        }
        
        final_state = await self.workflow.ainvoke(initial_state)
        return {
            "context_text": final_state['report'],
            "sources": final_state['sources']
        }
