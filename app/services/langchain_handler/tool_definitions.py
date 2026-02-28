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
    """Lookup specific data points, dates, or singular facts in the knowledge base. Use this for questions where a direct answer is enough."""
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
    count: int = Field(default=25, description="The number of research papers to return. Default is 25.")
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
    Advanced research tool that combines semantic search with document retrieval and response generation. Use this for complex research questions that require not just finding papers, but also extracting and summarizing key insights from them.

    This tool performs the following steps:
    1. Semantic Scholar Search: Uses the query to find relevant papers based on meaning, not just keywords.
    2. Article Retrieval: Fetches the full text of the most relevant papers.
    3. Article Indexing: Processes and indexes the retrieved articles for efficient access.
    4. Response Generation: Synthesizes a comprehensive answer to the user's query based on the indexed articles, highlighting key findings and insights.

    This is ideal for in-depth research questions where the user needs a synthesized answer derived from multiple academic sources.

    Example usage:
    User asks: "Get me some relevant research articles on the role of gut microbiome in neurodegenerative diseases and give me the relevant parts from those papers that helps my research on Parkinson's."
    search_query: '"gut microbiome" AND "neurodegenerative diseases" AND Parkinson's'
    original_query: "The role of gut microbiome in neurodegenerative diseases specifically focused on Parkinson's research."
    sub_queries: ["gut-brain axis Parkinson's disease research", "microbiome composition neurodegeneration", "therapeutic potential of probiotics in Parkinson's"]
    """
    
    original_query: str = Field(description="The complex research question or topic that requires an in-depth answer synthesized from multiple academic papers.")
    search_query: str = Field(description="A keyword-optimized search query for the academic database. Use Boolean operators (AND, OR, NOT) and exact phrases in quotes as defined in FetchResearch to find relevant papers.")
    sub_queries: List[str] = Field(description=(        
        "Semantically rewritten search queries derived from the original query and relevant context from the conversation history. "
        "Each item should be a full natural-language query optimized for vector retrieval, "
        "DO NOT return single words or keyword lists."))
    count: int = Field(default=5, description="The number of research papers to index. Default is 5.")

class InternalThought(BaseModel):
    """CONDITIONAL STEP. Use this tool to log your internal reasoning, planning, and risk assessments before taking any other action. Required for complex queries and before tool calls, but skip it for simple/direct greetings and basic questions."""
    reasoning: str = Field(description="Your detailed internal thought process, hypothesis, and plan of action.")

def get_tool_schemas():
    return [
        InternalThought,
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

