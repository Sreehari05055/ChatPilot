import json
from urllib.parse import urlparse
from openai.types.chat import ChatCompletionChunk
from app import logger
from typing import Optional, AsyncGenerator 
from typing import Callable
from io import StringIO
from app.core.config import Config

config = Config()

class ChatbotService:
    def __init__(self, llm_engine, web_search_service, web_fetch_service, rag_service, system_prompt, store, session_id, code_executor):
        self.llm_engine = llm_engine
        self.web_search_service = web_search_service
        self.web_fetch_service = web_fetch_service
        self.rag_service = rag_service
        self.system_message = system_prompt
        self.store = store
        self.code_executor = code_executor
        self.session_id = session_id
    
    def _trim_messages(self, message_list):
        max_msgs = config.MAX_CONVERSATION_TURNS
        if not max_msgs or max_msgs <= 0:
            return message_list
        
        trimmed = message_list[-max_msgs:]
        while trimmed and trimmed[0].get("role") == "tool":
                trimmed.pop(0)
        if trimmed and trimmed[-1].get("role") == "assistant" and trimmed[-1].get("tool_calls"):
            # Keep the last assistant message with tool_calls
            pass
        return trimmed

    def _update_system_message(self, context_chunks, file_metadata=None):
        """Build system message with RAG context."""
        logger.debug(f"File metadata for system message: {file_metadata}")
        if isinstance(file_metadata, dict) and "file_metadata" in file_metadata:
            file_metadata = file_metadata["file_metadata"]

        if not context_chunks:
            formatted_context = "No relevant knowledge base entries found for this specific query."
        elif isinstance(context_chunks, list):
            formatted_context = "\n".join(context_chunks)
        else:
            formatted_context = context_chunks
        msg = self.system_message.replace("{context}", formatted_context)

        if file_metadata:
            msg += "\n\nUPLOADED FILE METADATA:\n"
            for filename, metadata in file_metadata.items():
                msg += f"- {filename}: {metadata['shape'][0]} rows, {len(metadata['columns'])} columns\n"
                msg += f"  Columns: {', '.join(metadata['columns'])}\n"
                msg += f"  Numeric: {', '.join(metadata['numeric_columns'])}\n"
                msg += f"  Categorical: {', '.join(metadata['categorical_columns'])}\n"
        return msg
    
    def is_valid_http_url(self,url: str) -> bool:
        try:
            parsed = urlparse(url)
            return parsed.scheme in ("http", "https") and bool(parsed.netloc)
        except Exception:
            return False
    
    async def _gpt_engine(self, messages=None, system_prompt=None) -> Optional[AsyncGenerator[ChatCompletionChunk, None]]:
        try:
 
            response = self.llm_engine.stream_response(
                messages=messages,
                system_prompt=system_prompt,
                model=config.MODEL_NAME,
                top_p=config.TOP_P,
                max_completion_tokens=config.MAX_TOKENS,
                temperature=config.TEMPERATURE,
                stream=config.STREAM,
            )

            logger.info(f"Successfully used {config.MODEL_NAME} for response")
            return response
        except Exception as e:
            logger.error(f"Error with {config.MODEL_NAME}: {str(e)}", exc_info=True)
            return None

    async def _generate_response(self, query: str) -> AsyncGenerator[str, None]:
        """Generate a streaming response."""
        try:
            messages = await self.store.get_messages(self.session_id)

            file_metadata = await self.store.get_session_metadata(self.session_id)
            uploaded_files = await self.store.get_uploaded_file_paths(self.session_id)
            
            logger.info(f"Uploaded file paths: {uploaded_files}")
            logger.info(f"Uploaded file metadata: {file_metadata}")

            yield f"data: {json.dumps({'status': 'Searching knowledge base...'})}\n\n"
            try:
                context_chunks = await self.rag_service._get_corpus_data(query)
                if context_chunks:
                    logger.info(f"Retrieved {context_chunks} RAG context chunks")
            except Exception as e:
                logger.error(f"RAG failed: {e}")

            current_system_message = self._update_system_message(context_chunks, file_metadata.get("file_metadata", {}))
            
            new_msg = {"role": "user", "content": query}
            messages.append(new_msg)
            await self.store.add_message(self.session_id, new_msg)

            messages = self._trim_messages(messages)

            buffer = StringIO()

            for attempt in range(1, Config.MAIN_LLM_MAX_RETRIES + 1):
                logger.info(f"LLM response attempt {attempt}/{Config.MAIN_LLM_MAX_RETRIES}")

                function_called = False
                function_name = None
                tool_call_id = None
                function_args = StringIO()
                
                stream = await self._gpt_engine(messages=messages, system_prompt=current_system_message)
                
                async for chunk in stream:
                    if not chunk:
                        continue

                    ctype = chunk.get("type")
                    content = chunk.get("content")
                    func = chunk.get("function")

                    if ctype == "function_call" or func:
                        function_called = True
                        try:
                            name = func.get("name") if isinstance(func, dict) else getattr(func, "name", None)
                            if name:
                                function_name = name
                            args_frag = func.get("arguments_fragment") if isinstance(func, dict) else getattr(func, "arguments", None)
                            if args_frag:
                                function_args.write(args_frag)
                            if func.get("id"): tool_call_id = func["id"]
                        except Exception:
                            function_args.write(str(func))
                        continue

                    if ctype == "delta" and content:
                        buffer.write(content)
                        yield f"data: {json.dumps({'content': content}, ensure_ascii=False)}\n\n"
                
                if not function_called:
                    # No function called, break the retry loop
                    break


                args_str = function_args.getvalue()
                

                assistant_tool_msg = {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [{
                        "id": tool_call_id or "call_default",
                        "type": "function",
                        "function": {"name": function_name, "arguments": args_str}
                    }]
                }
                messages.append(assistant_tool_msg)
                await self.store.add_message(self.session_id, assistant_tool_msg)

                try:
                    if function_name == "web_search":
                        args = json.loads(args_str) if args_str.strip() else {}
                        search_query = args.get("question", query)
                        tool_content = await self.web_search_service.run_web_search(search_query)
                        
                    elif function_name == "web_fetch":
                        args = json.loads(args_str) if args_str.strip() else {}
                        url = args.get("url", "")
                        tool_content = await self.web_fetch_service.fetch_and_parse(url)
                        
                    elif function_name == "analyze_data":
                        args = json.loads(args_str) if args_str.strip() else {}
                        plan = args["analysis_plan"]
                        task_type = args["task_type"]
                        target = args.get("target_column")
                        risks = args.get("risk_checks", [])

                        result = await self.code_executor.generate_solution(plan, task_type, file_metadata, target, risks)
                        logger.debug(f"Code execution result: {result}")
                        success = bool(result.get("success"))
                        res = result.get("result")
                        code = result.get("code", "")
                        attempts = result.get("attempts", 0)
                        error = result.get("error")
                        retryable = error.get("retryable", False)
                        
                        if success:
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
                        else:
                            if error and not retryable:
                                
                                error_message = error.get('message', 'Unknown error')
                                error_category = error.get('category', 'Unknown')
                                logger.error(
                                    f"Stopping analysis: category={error_category} reason={error_message}"
                                )

                                # Send error as tool response
                                tool_content = (
                                    "ERROR: Analysis could not be completed.\n"
                                    f"Reason: {error_message}\n\n"
                                    "Do not attempt to retry this analysis automatically.\n"
                                    "Explain to the user what went wrong in plain language. "
                                    "If the issue appears related to the input data or request, suggest what they may want to check. "
                                    "If it does not clearly point to a user input issue, explain that it may be an internal problem and suggest trying again later."
                                )

                                tool_msg = {
                                    "role": "tool",
                                    "tool_call_id": tool_call_id or "call_default",
                                    "name": function_name,
                                    "content": tool_content
                                }
                                messages.append(tool_msg)
                                await self.store.add_message(self.session_id, tool_msg)
                                
                                # Get follow-up explanation from LLM
                                messages = self._trim_messages(messages)
                                followup_stream = await self._gpt_engine(
                                    messages=messages, 
                                    system_prompt=self._update_system_message([], file_metadata.get("file_metadata", {}))
                                )
                                
                                if followup_stream:
                                    async for chunk in followup_stream:
                                        if chunk.get("type") == "delta" and chunk.get("content"):
                                            buffer.write(chunk["content"])
                                            yield f"data: {json.dumps({'content': chunk['content']}, ensure_ascii=False)}\n\n"
                                
                                # Break out of retry loop after getting final explanation
                                break
                            else:
                                # Retryable error or other case
                                tool_content = f"Analysis attempt failed: {error.get('message', 'Unknown error') if error else 'Unknown error'}"    
                
                except Exception as e:
                    logger.error(f"Tool error: {e}")
                    tool_content = f"Error: {str(e)}"
                
                if not (function_name == "analyze_data" and error and not retryable):
                    
                    tool_msg = {
                        "role": "tool",
                        "tool_call_id": tool_call_id or "call_default",
                        "name": function_name,
                        "content": str(tool_content)
                    }

                    messages.append(tool_msg)
                    await self.store.add_message(self.session_id, tool_msg)
            
                    messages = self._trim_messages(messages)

            # Finalize
            final_response = buffer.getvalue()
            buffer.close()
            
            if final_response:
                ai_msg = {"role": "assistant", "content": final_response}
                messages.append(ai_msg)
                await self.store.add_message(self.session_id, ai_msg)
            
            logger.info(f"✅ RESPONSE COMPLETE")
            yield f"data: {json.dumps({'end': True})}\n\n"

        except Exception as e:
            logger.error(f"❌ ERROR in _generate_response: {e}")
            logger.error(f"Error in generate_response: {e}", exc_info=True)
            yield f"data: {json.dumps({'error': 'An error occurred'})}\n\n"
