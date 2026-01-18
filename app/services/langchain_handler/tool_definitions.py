from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class WebSearch(BaseModel):
    """Search the web for general knowledge, current events, or information NOT related to uploaded files. Do NOT use this for analyzing uploaded data."""
    question: str = Field(description="The user's question to be rephrased and web searched.")

class WebFetch(BaseModel):
    """Fetch and analyze the content of a specific URL provided by the user."""
    url: str = Field(description="The exact URL to fetch content from.")

class AnalyzeData(BaseModel):
    """REQUIRED for ANY questions about uploaded CSV/Excel files. Use this to perform data analysis, statistics, visualizations, filtering, aggregations, or machine learning on uploaded data. Check the UPLOADED FILE METADATA in the system message."""
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

class GetInfo(BaseModel):
    """Lookup specific data points, dates, or singular facts in the knowledge base. Use this for questions where a direct answer is enough."""
    topic: str = Field(description="The specific fact or entity to find.")

class GetInfoWithExplanation(BaseModel):
    """Analyze and connect multiple pieces of information from the knowledge base. Use this for questions that require a reasoned explanation of the data."""
    topics: List[str] = Field(description="Sub-topics to search before synthesizing.")

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
        AnalyzeData,
        GetInfo,
        GetInfoWithExplanation,
        ExtractMetadata,
        GenerateCode,
        ExecuteCode
    ]

