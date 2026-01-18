from app import logger
import json
from app.services.code_execution.base_handler_factory import BaseFileHandler

class ToolExecutor:
    def __init__(self, web_search_service, web_fetch_service, code_executor, rag_service):
        self.web_search = web_search_service
        self.web_fetch = web_fetch_service
        self.code_executor = code_executor
        self.rag_service = rag_service

    async def _execute_analyze_data(self, args, file_context):
        plan = args["analysis_plan"]    
        task_type = args["task_type"]
        target = args.get("target_column")
        risks = args.get("risk_checks", [])
        
        # safely get file_paths and metadata
        file_paths = file_context.get("file_paths", []) if isinstance(file_context, dict) else []
        metadata = file_context.get("file_metadata", {}) if isinstance(file_context, dict) else {}
        
        # calling the graph-based agent
        result = await self.code_executor.run_analysis_agent(plan, task_type, file_paths, metadata, target, risks)
        logger.debug(f"Analysis Agent result: {result}")
        
        success = result.get("success")
        error = result.get("error")
        
        if success:
            res = result.get("result")
            code = result.get("code", "")
            attempts = result.get("attempts", 0)
            if res:
                tool_content = (
                    "Analysis result:\n\n"
                    f"Result:\n{res}\n\n"
                    "Generated code:\n```python\n"
                    f"{code}\n```\n\n"
                    f"Attempts: {attempts}"
                )
            else:
                tool_content = "Analysis completed but no result was returned."
            return tool_content
        else:
            error_message = error.get('message', 'Unknown error')
            # ... (rest of error handling is similar but we used generic error structure)
            tool_content = (
                "ERROR: Analysis could not be completed.\n"
                f"Reason: {error_message}\n\n"
                "Do not attempt to retry this analysis automatically.\n"
                "Explain to the user what went wrong."
            )
            return tool_content

    async def _execute_extract_metadata(self, args, file_context):
        """Maps filenames provided by LLM to full paths and runs analysis."""
        requested_files = args.get("file_paths", []) # LLM might call it file_paths but pass filenames
        all_metadata = file_context.get("file_metadata", {})
        
        # Resolve filenames to full paths
        actual_paths = []
        for req_f in requested_files:
            # Check if it's already a path or if it matches a filename in our metadata
            found = False
            for path, meta in all_metadata.items():
                if req_f in path: # matches data.csv or /path/to/data.csv
                    actual_paths.append(path)
                    found = True
                    break
            if not found:
                return f"Error: File '{req_f}' not found in available files."
        
        results = await self.code_executor.analyze_files(actual_paths)
        return json.dumps(results, indent=2)

    async def _execute_generate_code(self, args, file_context):
        """Helper to call code generator tool directly."""
        metadata = args.get("metadata", {})
        query = args.get("query", "")
        # We can use the internal generator from code_executor
        code = await self.code_executor.code_generator.generate_code(
            analysis_plan=[query],
            task_type="general_analysis",
            metadata=metadata
        )
        return code

    async def _execute_execute_code(self, args, file_context):
        """Helper to run code tool directly."""
        code = args.get("code", "")
        # Clean and run
        cleaned = BaseFileHandler.clean_code_block(code)
        result = self.code_executor.code_executor.execute_code(cleaned)
        return json.dumps(result, indent=2)

    async def _execute_extract_metadata(self, args, file_context):
        """Reuses the 'analyze_metadata' node from our LangGraph."""
        requested_files = args.get("file_paths", [])
        all_metadata = file_context.get("file_metadata", {})
        
        # Mapping filename -> path
        actual_paths = []
        for req_f in requested_files:
            for path in all_metadata.keys():
                if req_f in path:
                    actual_paths.append(path)
                    break
        
        # Call the node directly with a temporary state
        temp_state = {"file_paths": actual_paths}
        result_state = await self.code_executor.analysis_graph.analyze_metadata_node(temp_state)
        
        return json.dumps(result_state.get("metadata", {}), indent=2)

    async def _execute_generate_code(self, args, file_context):
        """Reuses the 'generate_code' node from our LangGraph."""
        temp_state = {
            "metadata": args.get("metadata", {}),
            "user_query": args.get("query", ""),
            "attempts": 0
        }
        result_state = await self.code_executor.analysis_graph.generate_code_node(temp_state)
        return result_state.get("generated_code", "")

    async def _execute_execute_code(self, args, file_context):
        """Reuses the 'execute_code' node from our LangGraph."""
        temp_state = {"generated_code": args.get("code", "")}
        result_state = await self.code_executor.analysis_graph.execute_code_node(temp_state)
        
        return json.dumps(result_state.get("execution_result", {}), indent=2)

    async def execute(self, function_name, args_str, file_context=None):
        """Dynamic tool dispatcher."""
        try:
            # 1. Standardize the name (handle CamelCase or snake_case)
            # Map names from tool_definitions.py classes to their implementation methods
            dispatch_map = {
                "WebSearch": self._execute_web_search,
                "WebFetch": self._execute_web_fetch,
                "AnalyzeData": self._execute_analyze_data,
                "GetInfo": self._execute_get_info,
                "GetInfoWithExplanation": self._execute_get_info_with_explanation,
                "ExtractMetadata": self._execute_extract_metadata,
                "GenerateCode": self._execute_generate_code,
                "ExecuteCode": self._execute_execute_code,
                # also include snake_case for robustness
                "web_search": self._execute_web_search,
                "web_fetch": self._execute_web_fetch,
                "analyze_data": self._execute_analyze_data,
                "get_info": self._execute_get_info,
                "get_info_with_explanation": self._execute_get_info_with_explanation,
                "extract_metadata": self._execute_extract_metadata,
                "generate_code": self._execute_generate_code,
                "execute_code": self._execute_execute_code,
            }

            args = json.loads(args_str) if args_str.strip() else {}
            file_context = file_context or {}
            
            if function_name in dispatch_map:
                logger.info(f"🛠️ Executing tool: {function_name}")
                return await dispatch_map[function_name](args, file_context)
            else:
                logger.warning(f"❌ Unknown tool: {function_name}")
                return f"Error: Tool '{function_name}' is not registered."

        except Exception as e:
            logger.error(f"🚨 Tool failure [{function_name}]: {e}", exc_info=True)
            return f"Error executing {function_name}: {str(e)}"

    # --- Tool Implementation Wrappers ---

    async def _execute_web_search(self, args, ctx):
        return await self.web_search.run_web_search(args.get("question"))

    async def _execute_web_fetch(self, args, ctx):
        return await self.web_fetch.fetch_and_parse(args.get("url", ""))

    async def _execute_get_info(self, args, ctx):
        return await self.rag_service.get_info(args.get("topic"))

    async def _execute_get_info_with_explanation(self, args, ctx):
        return await self.rag_service.get_info_with_explanation(args.get("topics", []))