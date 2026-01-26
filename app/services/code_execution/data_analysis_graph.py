import os
from typing import TypedDict, Annotated, List, Union
from langgraph.graph import StateGraph, END
from app.core.config import Config
from app import logger
from app.services.code_execution.base_handler_factory import BaseFileHandler
from app.services.code_execution.file_handler_factory import FileHandlerFactory
from app.services.code_execution.code_generator import CodeGenerator
from app.services.code_execution.code_sandbox import CodeSandboxExecutor
from app.services.code_execution.error_classifier import ErrorClassifier

# Define the state of our graph
class AnalysisState(TypedDict):
    """
    Represents the state of the data analysis workflow.
    Shared data between Metadata, Coder, and Executor steps.
    """
    file_paths: List[str]            # Input: List of files to analyze
    user_query: str                  # Input: The user's question/request
    session_id: str                  # Input: Unique identifier for the user session
    
    metadata: dict                   # Artifact from Metadata Step
    analysis_plan: List[str]         # Plan generated (optional, or implicit in code gen)
    generated_code: str              # Artifact from Coder Step
    execution_result: dict | None    # Artifact from Execution Step
    
    error: str | None                # Track current error
    attempts: int                    # Retry counter for code generation

class DataAnalysisGraph:
    def __init__(self):
        self.code_generator = CodeGenerator()
        self.error_classifier = ErrorClassifier()
        self.code_executor = CodeSandboxExecutor(self.error_classifier)
        
        # Build the graph
        self.app = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(AnalysisState)

        # 1. Add Nodes
        workflow.add_node("analyze_metadata", self.analyze_metadata_node)
        workflow.add_node("generate_code", self.generate_code_node)
        workflow.add_node("execute_code", self.execute_code_node)

        # 2. Add Edges
        # Start -> Metadata
        workflow.set_entry_point("analyze_metadata")
        
        # Metadata -> Coder
        workflow.add_edge("analyze_metadata", "generate_code")
        
        # Coder -> Executor
        workflow.add_edge("generate_code", "execute_code")
        
        # Executor -> Decision (Retry or End)
        workflow.add_conditional_edges(
            "execute_code",
            self.should_continue,
            {
                "retry": "generate_code",
                "end": END
            }
        )

        return workflow.compile()

    # --- Node Implementations ---

    async def analyze_metadata_node(self, state: AnalysisState):
        """Step 1: Extract metadata from files. Skip if already exists."""
        if state.get("metadata") and len(state["metadata"]) > 0:
            logger.info("⏩ Metadata already provided. Skipping re-analysis.")
            return {"attempts": 0}

        logger.info("--- Graph Node: Metadata Analysis ---")
        filepaths = state.get("file_paths", [])
        results = {}
        for filepath in filepaths:
            # Reusing existing FileHandlerFactory logic
            handler = FileHandlerFactory.get_handler(filepath)
            metadata = handler.analyze_file(filepath)
            
            # Use basename as key so the LLM writes clean code (e.g. pd.read_csv('data.csv'))
            filename = os.path.basename(filepath)
            results[filename] = metadata
        
        return {"metadata": results, "attempts": 0}

    async def generate_code_node(self, state: AnalysisState):
        """Step 2: Generate Python code based on metadata and query."""
        logger.info(f"--- Graph Node: Code Generation (Attempt {state.get('attempts', 0) + 1}) ---")
        
        task_type = "general_analysis" 
        
        previous_code = state.get("generated_code")
        previous_error = state.get("error")
        
        analysis_plan = state.get("analysis_plan")
        if not analysis_plan:
            analysis_plan = [state.get("user_query", "Perform analysis")]
        
        code = await self.code_generator.generate_code(
            analysis_plan=analysis_plan,
            task_type=task_type,
            metadata=state["metadata"],
            previous_code=previous_code if previous_error else None,
            previous_error=previous_error
        )
        logger.info(f"--- Generated Code ---\n{code}\n--- End of Code ---")
        return {
            "generated_code": code, 
            "attempts": state.get("attempts", 0) + 1,
            "error": None # Clear previous error as we have new code
        }

    async def execute_code_node(self, state: AnalysisState):
        """Step 3: Execute the generated code."""
        logger.info("--- Graph Node: Code Execution ---")
        code = state["generated_code"]
        
        # Clean code
        cleaned_code = BaseFileHandler.clean_code_block(code)
        
        # Execute
        result = self.code_executor.execute_code(cleaned_code, session_id=state.get("session_id"),file_paths=state.get("file_paths", []))
        
        if result['success']:
            logger.info("--- Execution Success ---")
            return {"execution_result": result, "error": None}
        else:
            logger.warning(f"--- Execution Failed: {result.get('error')} ---")
            return {"execution_result": result, "error": result.get('error')}


    def should_continue(self, state: AnalysisState):
        """Decide whether to retry or end."""
        error = state.get("error")
        attempts = state.get("attempts", 0)
        
        if not error:
            return "end" # Success!
        
        if attempts >= Config.EXEC_MAX_RETRIES:
            logger.error("--- Max retries reached ---")
            return "end" # Give up
            
        execution_result = state.get("execution_result", {})
        error_details = execution_result.get("error_details", {})
        if error_details.get("category") == "NON_RETRYABLE":
             return "end"

        return "retry"

    async def run(self, input_state: AnalysisState):
        """Entry point to run the graph."""
        return await self.app.ainvoke(input_state)
