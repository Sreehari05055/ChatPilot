from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, Literal

class WebSearch(BaseModel):
    """Search the web for general knowledge, current events, or information NOT related to uploaded files. Do NOT use this for analyzing uploaded data."""
    question: str = Field(description="The user's question to be rephrased and web searched.")
    topic: Optional[Literal["general", "news", "finance"]] = Field(default="general", description="The search category. Use 'news' or 'finance' for more specialized results.")
    time_range: Optional[Literal["day", "week", "month", "year"]] = Field(default=None, description="The time range to restrict search results to. Mutually exclusive with start_date and end_date.")
    start_date: Optional[str] = Field(default=None, description="Start date for search results (YYYY-MM-DD format). Mutually exclusive with time_range.")
    end_date: Optional[str] = Field(default=None, description="End date for search results (YYYY-MM-DD format). Mutually exclusive with time_range.")

    @model_validator(mode='after')
    def validate_date_params(self) -> 'WebSearch':
        if self.time_range and (self.start_date or self.end_date):
            raise ValueError("When time_range is set, start_date or end_date cannot be set")
        return self
    
class WebFetch(BaseModel):
    """Fetch and analyze the content of a specific URL provided by the user."""
    url: str = Field(description="The exact URL to fetch content from.")

class WebResearch(BaseModel):
    """Perform deep, agentic research on a complex topic. Use this when the user asks for a 'deep dive', 'thorough report', or a detailed analysis of a current event or complex subject."""
    topic: str = Field(description="The complex topic or question that requires a multi-step research report.")

class AnalyzeData(BaseModel):
    """REQUIRED for ANY questions about uploaded CSV/Excel files. Use this to perform data analysis, statistics, visualizations, filtering, aggregations, or machine learning on uploaded data. If you don't know which files are available, call ListFiles first."""
    analysis_plan: List[str] = Field(description="Ordered, concrete analysis steps to perform. Each step must be specific and actionable.")
    task_type: Literal[
        "eda",
        "aggregation",
        "filtering",
        "statistics",
        "ml_classification",
        "ml_regression",
        "clustering",
        "time_series"
    ] = Field(description="The type of analysis task to perform.")
    target_column: Optional[str] = Field(None, description="Target variable for ML tasks, null otherwise.")
    risk_checks: Optional[List[str]] = Field(default=[], description="Specific risk or bias checks to perform on the data or model.")

class ListFiles(BaseModel):
    """List all files that the user has uploaded to this session. Use this if the user asks 'what files did I upload?' or if you need to find a filename to analyze."""
    pass

class GetInfo(BaseModel):
    """Lookup specific data points, dates, or singular facts in the knowledge base. Use this for questions where a direct answer is enough. Also use this for follow-up questions about papers that have already been downloaded and indexed; do not call DeepScholarResearchAndHighlight again unless new papers need to be searched or downloaded."""
    topic: List[str] = Field(description=(        
        "Semantically rewritten search queries derived from the user question. "
        "Each item should be a full natural-language query optimized for vector retrieval, "
        "DO NOT return single words or keyword lists."))
    question: str = Field(description=(        
        "A minimally normalized version of the original question "
        "(e.g., resolving pronouns), without changing scope or intent."))

class ExtractMetadata(BaseModel):
    """Extract column names, types, and summary info from specific uploaded files."""
    file_paths: List[str] = Field(description="Paths to the files to analyze.")

class GenerateCode(BaseModel):
    """Generate Python code for a data task. Requires file metadata."""
    metadata: dict = Field(description="The metadata dictionary obtained from ExtractMetadata.")
    query: str = Field(description="The specific transformation or analysis to perform.")

class ExecuteCode(BaseModel):
    """Run Python code in the sandbox and return the result/plots."""
    code: str = Field(description="The Python code to execute.")

class PaperMetadata(BaseModel):
    """Metadata for a previously fetched research paper."""
    id: str = Field(description="The OpenAlex work ID (e.g., 'W2741809807'). Used to construct the download URL.")
    title: str = Field(description="The paper title. Used for generating the filename.")
    pdf_url: Optional[str] = Field(default=None,description="Direct PDF download URL. Used as fallback if the Content API fails.")
    authors: Optional[List[str]] = Field(default=None,description="List of author names.")
    publication_year: Optional[int] = Field(default=None,description="Year of publication.")
    doi: Optional[str] = Field(default=None,description="DOI identifier.")

class FetchResearch(BaseModel):
    """
    OpenAlex keyword search API for finding research papers.
    This tool is for retrieving academic papers based on keyword queries. It returns structured metadata about relevant papers, title, authors, year, DOI, is_open_access, pdf_url. Use this when the user needs to find research literature on a specific topic or question.

    SEARCH CAPABILITIES:
    - Simple keywords: "machine learning drug discovery"
    - Boolean operators (MUST BE UPPERCASE): AND, OR, NOT
    Example: '("machine learning" OR AI) AND "drug discovery" NOT review'
    - Exact phrases: Use double quotes "deep learning"
    - Grouping: Use parentheses to control logic (term1 AND term2) OR term3
    - Default: Words without operators are treated as AND
    
    USAGE EXAMPLES:
    query='machine learning AND "drug discovery"'  # Both terms required
    query='(AI OR "machine learning") AND medicine NOT review'  # Complex boolean
    query='"deep learning" AND cancer'  # Exact phrase + keyword

    NOT SUPPORTED:
    - Wildcards (*, ?)
    - Fuzzy matching (~)
    - Semantic/meaning-based search (use keyword matching only)
    """
    
    query: str = Field(description="The user's research query to find relevant academic papers. This should be a natural language question or topic (e.g., 'What are the latest advancements in CRISPR gene editing?').")
    count: int = Field(default=10, description="The number of research papers to return. Default is 10.")
    publication_year: Optional[str] = Field(
        default=">1950",
        description="Filter by year (e.g., '2023', '>2020', or '2020-2023'). Default is '>1950'."
    )
    is_oa: Optional[bool] = Field(
        default=True,
        description="Set to true to return only Open Access works. Default is True."
    )
    has_pdf: Optional[bool] = Field(
        default=True,
        description="Set to true to ensure the paper has a downloadable PDF. Default is True."
    )


class DeepScholarResearchAndHighlight(BaseModel):
    """
    Advanced research tool that downloads, indexes, and RAGs academic papers to synthesize answers.

    Use this only when you need to search for new papers or download/index papers that are not already available.
    For follow-up questions about papers that were already downloaded and indexed in the current session, use GetInfo instead of calling this tool again.

    TWO MODES OF OPERATION:

    Mode 1 — Full pipeline (search + download + index + RAG):
    Provide `search_query` to search for new papers. The tool will find papers, download them, index them, and generate a report.

    Mode 2 — Skip search (download + index + RAG from prior results):
    If papers were already fetched in a previous turn via FetchResearch, pass them in `paper_metadata` and omit `search_query`. The tool will skip the search step and directly download, index, and RAG those papers.

    CRITICAL — BATCHING RULE:
    Always pass ALL relevant papers in a SINGLE call via `paper_metadata`. NEVER split papers across multiple calls.
    The tool handles multiple papers internally — it downloads all, builds one unified index, and generates one comprehensive report.
    Splitting papers into separate calls causes redundant index rebuilds and wastes time.

    Example Mode 1 (fresh search):
    User asks: "Get me research on gut microbiome in Parkinson's and highlight the relevant parts."
    search_query: '"gut microbiome" AND "neurodegenerative diseases" AND Parkinson\'s'
    original_query: "The role of gut microbiome in neurodegenerative diseases focused on Parkinson's."
    sub_queries: ["gut-brain axis Parkinson's disease", "microbiome composition neurodegeneration"]

    Example Mode 2 (prior FetchResearch results — ALL papers in one call):
    User asks: "Download those papers you found and tell me what they say about dopamine pathways."
    original_query: "Dopamine pathway mechanisms discussed in the fetched papers."
    sub_queries: ["dopamine pathway mechanisms", "neurotransmitter regulation"]
    paper_metadata: [{"id": "W2741809807", ...}, {"id": "W3148293100", ...}, {"id": "W1234567890", ...}]
    """
    
    original_query: str = Field(description="The complex research question or topic that requires an in-depth answer synthesized from multiple academic papers.")
    search_query: Optional[str] = Field(default=None, description="A keyword-optimized search query for the academic database. Required for Mode 1 (fresh search). Omit when providing paper_metadata from a previous FetchResearch call.")
    sub_queries: List[str] = Field(description=(
        "Semantically rewritten search queries derived from the original query and relevant context from the conversation history. "
        "Each item should be a full natural-language query optimized for vector retrieval, "
        "DO NOT return single words or keyword lists."))
    paper_metadata: Optional[List[PaperMetadata]] = Field(default=None, description="Pre-fetched paper metadata from a previous FetchResearch call. When provided, the search step is skipped and these papers are downloaded directly. Each entry needs at minimum 'id' and 'title'.")
    count: int = Field(default=5, description="The number of research papers to search for (only used in Mode 1). Default is 5.")


    @model_validator(mode='after')
    def validate_mode(self) -> 'DeepScholarResearchAndHighlight':
        """
        Enforce the input contract:
        - At least one of `search_query` or `paper_metadata` must be provided.
        - If `paper_metadata` is provided, it must be a non-empty list.
        """
        search_query = (self.search_query or "").strip()
        if self.paper_metadata is not None and not self.paper_metadata:
            raise ValueError("`paper_metadata` must be a non-empty list when provided.")
        if not search_query and self.paper_metadata is None:
            raise ValueError(
                "Provide either a non-empty `search_query` or a non-empty `paper_metadata` list."
            )
        return self
    
def get_tool_schemas():
    return [
        AnalyzeData,
        ExecuteCode,
        ExtractMetadata,
        GenerateCode,
        GetInfo,
        ListFiles,
        WebFetch,
        WebResearch,
        WebSearch,
        FetchResearch,
        DeepScholarResearchAndHighlight,
    ]

