import os
from app.services.code_execution.error_classifier import ErrorClassifier
from app.services.code_execution.file_handler_factory import FileHandlerFactory
from app.services.code_execution.code_generator import CodeGenerator
from app.services.code_execution.code_sandbox import CodeSandboxExecutor
from app.services.code_execution.base_handler_factory import BaseFileHandler
from app import logger
from app.core.config import Config
from app.services.code_execution.data_analysis_graph import DataAnalysisGraph, AnalysisState

class CodeExecutionService:
    def __init__(self):
        self.code_generator = CodeGenerator()
        self.error_classifier = ErrorClassifier()
        self.code_executor = CodeSandboxExecutor(self.error_classifier)
        self.analysis_graph = DataAnalysisGraph()
    
    async def analyze_files(self, filepaths: list) -> dict:
        """Analyze uploaded files, return metadata."""
        results = {}
        for filepath in filepaths:
            handler = FileHandlerFactory.get_handler(filepath)
            metadata = handler.analyze_file(filepath)
            results[filepath] = metadata
        return results
    
    async def run_analysis_agent(self, analysis_plan: list[str], task_type: str, session_id: str, store: any, target_column: str | None = None, risk_checks: list[str] | None = None) -> dict:
        """
        Executes the Data Analysis Agent (LangGraph).
        Resolves its own files and metadata from the session store.
        """
        # Resolve Context
        file_context = await store.get_session_metadata(session_id)
        upload_dir = store.get_session_upload_dir(session_id)
        
        file_names = file_context.get("file_paths", [])
        actual_paths = [os.path.join(upload_dir, f) for f in file_names]
        metadata = file_context.get("file_metadata", {})

        logger.info(f"🚀 Starting Data Analysis Agent for session: {session_id}")
        
        # 1. Prepare Initial State
        initial_state: AnalysisState = {
            "file_paths": actual_paths,
            "session_id": session_id,
            "user_query": f"Task Type: {task_type}. Plan: {analysis_plan}",
            "metadata": metadata,
            "analysis_plan": analysis_plan,
            "generated_code": "",
            "execution_result": None,
            "error": None,
            "attempts": 0
        }
        
        # 2. Invoke the Graph
        final_state = await self.analysis_graph.run(initial_state)
        
        # 3. Extract Result
        execution_result = final_state.get("execution_result")
        
        if execution_result and execution_result['success']:
            return {
                'success': True,
                'result': execution_result['result'],
                'code': final_state.get("generated_code"),
                'attempts': final_state.get("attempts", 0)
            }
        else:
             error_msg = final_state.get("error") or "Unknown error in analysis graph"
             return {
                "success": False,
                "error": {"message": str(error_msg), "category": "runtme_error"},
                "code": final_state.get("generated_code"),
                "attempts": final_state.get("attempts", 0)
            }