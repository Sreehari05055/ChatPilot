from app import logger
import json
from app.services.code_execution.base_handler_factory import BaseFileHandler

class ToolExecutor:
    def __init__(self, http_client=None):
        from app.services.web.web_search_factory import WebSearchProviderFactory
        from app.services.code_execution.execution_service import CodeExecutionService
        from app.services.rag_service.rag_execution_service import RAGExecutionService

        self.web_search_service = WebSearchProviderFactory.get_provider(http_client=http_client)
        self.code_executor = CodeExecutionService()
        self.rag_service = RAGExecutionService()

    async def execute(self, function_name, args_str, file_context=None, session_id=None, store=None):
        """Dynamic tool dispatcher."""
        try:
            dispatch_map = {
                "WebSearch": self._execute_web_search,
                "WebFetch": self._execute_web_fetch,
                "WebResearch": self._execute_web_research,
                "AnalyzeData": self._execute_analyze_data,
                "GetInfo": self._execute_get_info,
                "ExtractMetadata": self._execute_extract_metadata,
                "GenerateCode": self._execute_generate_code,
                "ExecuteCode": self._execute_code,
                # snake_case mapping
                "web_search": self._execute_web_search,
                "web_fetch": self._execute_web_fetch,
                "web_research": self._execute_web_research,
                "analyze_data": self._execute_analyze_data,
                "get_info": self._execute_get_info,
                "extract_metadata": self._execute_extract_metadata,
                "generate_code": self._execute_generate_code,
                "execute_code": self._execute_code,
            }

            args = json.loads(args_str) if args_str.strip() else {}
            
            # Encapsulate context for the wrappers
            ctx = {
                "file_context": file_context or {},
                "session_id": session_id,
                "store": store
            }
            
            if function_name in dispatch_map:
                logger.info(f"🛠️ Executing tool: {function_name}")
                return await dispatch_map[function_name](args, ctx)
            else:
                logger.warning(f"❌ Unknown tool: {function_name}")
                return f"Error: Tool '{function_name}' is not registered."

        except Exception as e:
            logger.error(f"🚨 Tool failure [{function_name}]: {e}", exc_info=True)
            return f"Error executing {function_name}: {str(e)}"

    # --- Tool Implementation Wrappers ---

    async def _execute_web_search(self, args, ctx):
        query = args.pop("question")
        return await self.web_search_service.run_web_search(query, **args)

    async def _execute_web_fetch(self, args, ctx):
        return await self.web_search_service.web_fetch(args.get("url", ""))

    async def _execute_web_research(self, args, ctx):
        return await self.web_search_service.web_research(args.get("topic"))

    async def _execute_get_info(self, args, ctx):
        return await self.rag_service.get_info(args.get("topic"))

    async def _execute_extract_metadata(self, args, ctx):
        """
        Targeted metadata extraction. 
        Resolves filenames to full paths and analyzes ONLY what is requested.
        Saves resulting metadata back to the session store.
        """
        requested_files = args.get("file_paths", []) # LLM might pass ['data.csv']
        file_context = ctx["file_context"]
        session_id = ctx["session_id"]
        store = ctx["store"]

        all_paths = file_context.get("file_paths", [])
        existing_metadata = file_context.get("file_metadata", {})

        actual_paths = []
        for req_f in requested_files:
            found = False
            for path in all_paths:
                # Matches if the filename is in the path OR if it matches exactly
                if req_f in path or req_f == path:
                    actual_paths.append(path)
                    found = True
                    break
            if not found:
                return f"Error: File '{req_f}' not found in available session files."

        # Analyze the requested files
        new_metadata = await self.code_executor.analyze_files(actual_paths)
        
        # Merge with existing metadata
        updated_metadata = {**existing_metadata, **new_metadata}
        
        # PERSIST: Save back to the session history so it's available in future turns
        if session_id and store:
            logger.info(f"💾 Persisting JIT metadata for session {session_id}")
            await store.save_session_metadata(session_id, file_metadata=updated_metadata)
            # Update the local context so it's available immediately for tools in THIS turn
            file_context["file_metadata"] = updated_metadata

        return json.dumps(new_metadata, indent=2)

    async def _execute_analyze_data(self, args, ctx):
        file_context = ctx["file_context"]
        file_paths = file_context.get("file_paths", [])
        metadata = file_context.get("file_metadata", {})
        
        # Trigger the full LangGraph analysis agent
        result = await self.code_executor.run_analysis_agent(
            args["analysis_plan"],
            args["task_type"],
            file_paths,
            metadata,
            args.get("target_column"),
            args.get("risk_checks", [])
        )
        
        if result.get("success"):
            return (
                "Analysis result:\n\n"
                f"Result:\n{result.get('result')}\n\n"
                "Generated code:\n```python\n"
                f"{result.get('code')}\n```"
            )
        else:
            return f"ERROR: {result.get('error', {}).get('message', 'Unknown error')}"

    async def _execute_generate_code(self, args, ctx):
        """Direct code generation using the graph node."""
        temp_state = {
            "metadata": args.get("metadata", {}),
            "user_query": args.get("query", ""),
            "attempts": 0
        }
        result_state = await self.code_executor.analysis_graph.generate_code_node(temp_state)
        return result_state.get("generated_code", "")

    async def _execute_code(self, args, ctx):
        """Direct code execution using the graph node."""
        temp_state = {"generated_code": args.get("code", "")}
        result_state = await self.code_executor.analysis_graph.execute_code_node(temp_state)
        return json.dumps(result_state.get("execution_result", {}), indent=2)