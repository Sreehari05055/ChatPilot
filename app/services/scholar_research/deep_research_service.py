import os
import httpx
from typing import TypedDict, Annotated, List, Union, Dict
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

    def _create_workflow(self):
        workflow = StateGraph(ResearchState)
        
        workflow.add_node("search_papers", self.search_papers)
        workflow.add_node("download_papers", self.download_papers)
        workflow.add_node("index_papers", self.index_papers)
        workflow.add_node("generate_report", self.generate_report)
        
        workflow.set_entry_point("search_papers")
        workflow.add_edge("search_papers", "download_papers")
        workflow.add_edge("download_papers", "index_papers")
        workflow.add_edge("index_papers", "generate_report")
        workflow.add_edge("generate_report", END)
        
        return workflow.compile()

    async def search_papers(self, state: ResearchState):
        logger.info(f"Searching papers for: {state['search_query']} (Original: {state['original_query']})")
        results = await self.research_service.semantic_scholar_search(state['search_query'], count=5)
        
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
                    
                    logger.info(f"Downloading {paper['title']} from {pdf_url}")
                    # Standard User-Agent set in headers
                    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
                    response = await client.get(pdf_url, headers=headers, follow_redirects=True)
                    
                    if response.status_code == 200:
                        with open(filepath, "wb") as f:
                            f.write(response.content)
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
        
        # In a real scenario, we might call an LLM here to synthesize the report.
        # For this implementation, we return the context as a base for the LLM that called this tool.
        
        report = f"Research Report for: {state['original_query']}\n\n"
        report += "Papers Analyzed:\n"
        for paper in state['paper_metadata']:
             report += f"- {paper['title']} ({paper['publication_year']})\n"
        
        report += "\nKey Insights from Documents:\n"
        report += context
        
        return {"report": report, "sources": sources}

    async def run_research(self, original_query: str, search_query: str, sub_queries: List[str]):
        initial_state = {
            "original_query": original_query,
            "search_query": search_query,
            "sub_queries": sub_queries,
            "paper_metadata": [],
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
