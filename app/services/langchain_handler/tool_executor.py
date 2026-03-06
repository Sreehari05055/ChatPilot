from app import logger
import json
from app.services.code_execution.base_handler_factory import BaseFileHandler
import os

class ToolExecutor:
    def __init__(self, web_search_provider=None, rag_pipeline=None, http_client=None, research_provider=None):
        from app.services.web.web_search_factory import WebSearchProviderFactory
        from app.services.code_execution.execution_service import CodeExecutionService
        from app.services.rag_service.rag_execution_service import RAGExecutionService
        from app.services.scholar_research.factory import ResearchProviderFactory
        # Use injected provider or fallback to factory (for backwards compatibility)
        self.web_search_service = web_search_provider or WebSearchProviderFactory.get_provider(http_client=http_client)
        self.code_executor = CodeExecutionService()
        self.rag_service = RAGExecutionService(pipeline=rag_pipeline)
        self.research_service = research_provider or ResearchProviderFactory.get_provider(http_client=http_client)

    async def execute(self, function_name, args_str, session_id=None, store=None):
        """Dynamic tool dispatcher."""
        try:
            dispatch_map = {
                "WebSearch": self._execute_web_search,
                "WebFetch": self._execute_web_fetch,
                "WebResearch": self._execute_web_research,
                "AnalyzeData": self._execute_analyze_data,
                "GetInfo": self._execute_get_info,
                "ExtractMetadata": self._execute_extract_metadata,
                "ListFiles": self._execute_list_files, 
                "GenerateCode": self._execute_generate_code,
                "ExecuteCode": self._execute_code,
                "FetchResearch": self._fetch_research, 
                "DeepScholarResearchAndHighlight": self._execute_deep_scholar_research,
            }

            args = json.loads(args_str) if args_str.strip() else {}
            
            # Context for the wrappers
            ctx = {
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
        # Clean up args to remove None or 'null' values that Tavily might reject
        clean_args = {k: v for k, v in args.items() if v is not None and v != "null"}
        return await self.web_search_service.run_web_search(query, **clean_args)

    async def _execute_web_fetch(self, args, ctx):
        return await self.web_search_service.web_fetch(args.get("url", ""))

    async def _execute_web_research(self, args, ctx):
        research_results = await self.web_search_service.web_research(args.get("topic"))
        logger.info(f"Web research results received")
        return research_results

    async def _execute_deep_scholar_research(self, args, ctx):
        """Execute the multi-step research workflow."""
        from app.services.scholar_research.deep_research_service import DeepScholarResearchService
        deep_research_service = DeepScholarResearchService(
            research_provider=self.research_service, 
            rag_service=self.rag_service
        )
        return await deep_research_service.run_research(
            original_query=args.get("original_query"),
            search_query=args.get("search_query"),
            sub_queries=args.get("sub_queries", []),
            count=args.get("count", 5)
        )

    async def _execute_get_info(self, args, ctx):
        return await self.rag_service.get_info(
            queries=args.get("topic"),
            user_query=args.get("question")
        )

    async def _execute_extract_metadata(self, args, ctx):
        """
        Targeted metadata extraction. 
        Fetches fresh metadata from store and analyzes only requested files.
        """
        requested_files = args.get("file_paths", [])
        session_id = ctx["session_id"]
        store = ctx["store"]

        # Fetch fresh context inside the tool
        file_context = await store.get_session_metadata(session_id)
        upload_dir = store.get_session_upload_dir(session_id)
        existing_metadata = file_context.get("file_metadata", {})

        actual_paths = []
        for req_f in requested_files:
            clean_name = os.path.basename(req_f)
            path = os.path.join(upload_dir, clean_name)
            
            if os.path.exists(path):
                actual_paths.append(path)
            else:
                return f"Error: File '{clean_name}' not found."

        # Analyze
        new_metadata = await self.code_executor.analyze_files(actual_paths)
        
        # Merge & Persist
        updated_metadata = {**existing_metadata, **new_metadata}
        if session_id and store:
            logger.info(f"💾 Persisting JIT metadata for session {session_id}")
            await store.save_session_metadata(session_id, file_metadata=updated_metadata)

        clean_results = {os.path.basename(k): v for k, v in new_metadata.items()}
        return json.dumps(clean_results, indent=2)

    async def _execute_analyze_data(self, args, ctx):
        """
        Trigger the full Data Analysis Agent.
        The service itself will handle path resolution and metadata fetching.
        """
        result = await self.code_executor.run_analysis_agent(
            analysis_plan=args["analysis_plan"],
            task_type=args["task_type"],
            session_id=ctx["session_id"],
            store=ctx["store"],
            target_column=args.get("target_column"),
            risk_checks=args.get("risk_checks", [])
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

    async def _execute_list_files(self, args, ctx):
        """List all files available in the current session."""
        session_id = ctx["session_id"]
        store = ctx["store"]
        metadata = await store.get_session_metadata(session_id)
        files = metadata.get("file_paths", [])
        
        if not files:
            return "No files have been uploaded to this session yet."
        
        return f"The following files are available in this session: {', '.join(files)}"

    async def _execute_generate_code(self, args, ctx):
        """Direct code generation."""
        temp_state = {
            "metadata": args.get("metadata", {}),
            "user_query": args.get("query", ""),
            "attempts": 0
        }
        result_state = await self.code_executor.analysis_graph.generate_code_node(temp_state)
        return result_state.get("generated_code", "")

    async def _execute_code(self, args, ctx):
        """Direct code execution."""
        session_id = ctx["session_id"]
        store = ctx["store"]
        
        # Fresh resolution inside the service call
        file_context = await store.get_session_metadata(session_id)
        upload_dir = store.get_session_upload_dir(session_id)
        file_names = file_context.get("file_paths", [])
        actual_paths = [os.path.join(upload_dir, f) for f in file_names]

        temp_state = {
            "generated_code": args.get("code", ""), 
            "session_id": session_id, 
            "file_paths": actual_paths
        }
        result_state = await self.code_executor.analysis_graph.execute_code_node(temp_state)
        return json.dumps(result_state.get("execution_result", {}), indent=2)
    
    async def _fetch_research(self, args, ctx):
        """Fetch research using the web research tool as a placeholder."""
        query = args.get("query", "")
        count = args.get("count")    
        publication_year = args.get("publication_year")
        is_oa = args.get("is_oa")
        has_pdf = args.get("has_pdf")
        
        # For demonstration, we reuse the web research method. In a real implementation, this would call a dedicated research service.
        research_results = await self.research_service.get_formatted_search_results(query=query, count=count, publication_year=publication_year, is_oa=is_oa, has_pdf=has_pdf)
        
        logger.info(f"FetchResearch results received: {research_results}")
        return research_results