from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class WebSearch(BaseModel):
    """Search the web for general knowledge, current events, or information NOT related to uploaded files. Do NOT use this for analyzing uploaded data."""
    question: str = Field(description="The user's question to be rephrased and web searched.")
    topic: Optional[Literal["general", "news", "finance"]] = Field(default="general", description="The search category. Use 'news' or 'finance' for more specialized results.")
    time_range: Optional[Literal["day", "week", "month", "year"]] = Field(default=None, description="The time range to restrict search results to.")
    start_date: Optional[str] = Field(default=None, description="Start date for search results (YYYY-MM-DD format).")
    end_date: Optional[str] = Field(default=None, description="End date for search results (YYYY-MM-DD format).")
    
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

def get_tool_schemas():
    return [
        WebSearch,
        WebFetch,
        WebResearch,
        AnalyzeData,
        GetInfo,
        ExtractMetadata,
        ListFiles,
        GenerateCode,
        ExecuteCode
    ]

