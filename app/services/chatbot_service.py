import json
import asyncio
from typing import AsyncGenerator, List, Dict, Any
from app import logger
from app.core.config import Config
from app.services.langchain_handler.langchain_service import LangChainService
from app.services.langchain_handler.tool_definitions import get_tool_schemas
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage, BaseMessage
from langchain_core.output_parsers import StrOutputParser
import os   

config = Config()

class ChatbotService:
    def __init__(self, system_prompt: str, store, session_id: str, http_client):
        from app.services.langchain_handler.tool_executor import ToolExecutor
        self.system_prompt = system_prompt
        self.store = store
        self.session_id = session_id
        self.http_client = http_client
        self.tool_executor = ToolExecutor(http_client=http_client)
        self.llm = LangChainService.get_llm()
        self.tools = get_tool_schemas()
        self.llm_with_tools = self.llm.bind_tools(self.tools)

    def _update_system_message(self, context_chunks=None, file_context=None):
        """Build system message with RAG context."""
        file_context = file_context or {}
        file_metadata = file_context.get("file_metadata", {})
        file_paths = file_context.get("file_paths", [])
        
        formatted_context = "No relevant knowledge base entries found."
        if context_chunks:
            if isinstance(context_chunks, list):
                formatted_context = "\n".join(context_chunks)
            else:
                formatted_context = str(context_chunks)

        msg = self.system_prompt.replace("{context}", formatted_context)

        msg = self.system_prompt.replace("{context}", formatted_context)

        # Ensure all existing files are listed, regardless of metadata status
        if file_paths:
            msg += "\n\nAVAILABLE FILES (Session Context):\n"
            for i, path in enumerate(file_paths):
                filename = os.path.basename(path)
                meta_tag = ""
                
                # Check if we have metadata for this path
                if path in file_metadata:
                    meta_tag = " [Full Schema Available]"
                elif filename in file_metadata: 
                    meta_tag = " [Full Schema Available]"
                else:
                    meta_tag = " [Path Only - Use 'extract_metadata' to see columns]"
                
                msg += f"- {path}{meta_tag}\n"
            
            msg += "\nTo analyze or get details for any file, use 'extract_metadata' with the exact paths listed above."
        
        return msg

    def _convert_to_langchain_messages(self, stored_messages: List[Dict[str, Any]]) -> List[BaseMessage]:
        """Convert stored JSON messages to LangChain Message objects."""
        lc_messages = []
        for msg in stored_messages:
            role = msg.get("role")
            content = msg.get("content", "")
            
            if role == "user":
                lc_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                tool_calls = msg.get("tool_calls", [])
                # Reconstruct tool calls if present
                lc_tool_calls = []
                for tc in tool_calls:
                   # stored tool calls usually have id, function: {name, arguments}
                   lc_tool_calls.append({
                       "id": tc.get("id"),
                       "name": tc.get("function", {}).get("name"),
                       "args": json.loads(tc.get("function", {}).get("arguments", "{}")),
                       "type": "tool_call"
                   })
                
                lc_messages.append(AIMessage(content=content or "", tool_calls=lc_tool_calls))
            elif role == "tool":
                lc_messages.append(ToolMessage(
                    tool_call_id=msg.get("tool_call_id"), 
                    content=content,
                    name=msg.get("name") # Optional but good practice
                ))
            elif role == "system":
                 lc_messages.append(SystemMessage(content=content))
        return lc_messages

    async def _generate_response(self, query: str) -> AsyncGenerator[str, None]:
        try:
            # 1. Load History & Metadata
            stored_msgs = await self.store.get_messages(self.session_id)
            
            file_metadata_full = await self.store.get_session_metadata(self.session_id)
            current_system_msg = self._update_system_message(file_context=file_metadata_full)

            # 3. Prepare User Message
            user_msg = {"role": "user", "content": query}
            await self.store.add_message(self.session_id, user_msg)
            stored_msgs.append(user_msg)
            
            # 4. Prepare LangChain Messages
            # Ensure system message is first
            lc_messages = [SystemMessage(content=current_system_msg)] + self._convert_to_langchain_messages(stored_msgs)

            # 5. Main Loop (for tool calls)
            while True:
                # Stream response while accumulating for consistency
                accumulated_msg = None
                
                async for chunk in self.llm_with_tools.astream(lc_messages):
                    if accumulated_msg is None:
                        accumulated_msg = chunk
                    else:
                        accumulated_msg += chunk
                    
                    # Stream textual content to user
                    if chunk.content:
                         yield f"data: {json.dumps({'content': chunk.content}, ensure_ascii=False)}\n\n"
                
                if not accumulated_msg:
                    break
                
                # Store Assistant Message
                # Convert AIMessage to dict format for storage
                ai_msg_dict = {
                    "role": "assistant",
                    "content": accumulated_msg.content,
                }
                
                if accumulated_msg.tool_calls:
                    # It decided to call tools
                    tool_calls_data = []
                    for tc in accumulated_msg.tool_calls:
                        tool_calls_data.append({
                            "id": tc["id"],
                            "type": "function", # OpenAI standard
                            "function": {
                                "name": tc["name"],
                                "arguments": json.dumps(tc["args"]) 
                            }
                        })
                    ai_msg_dict["tool_calls"] = tool_calls_data
                    
                    # Store it
                    await self.store.add_message(self.session_id, ai_msg_dict)
                    lc_messages.append(accumulated_msg)

                    # Execute Tools
                    for tc in accumulated_msg.tool_calls:
                        tool_name = tc["name"]
                        tool_args = tc["args"] # Dict
                        tool_id = tc["id"]
                        
                        logger.info(f"Invoking tool: {tool_name} with args: {tool_args}")
                        
                        tool_result_content = await self.tool_executor.execute(
                            tool_name, 
                            json.dumps(tool_args), 
                            file_metadata_full,
                            self.session_id,
                            self.store
                        )
                        
                        # Create Tool Message
                        tool_msg_dict = {
                            "role": "tool",
                            "tool_call_id": tool_id,
                            "name": tool_name,
                            "content": str(tool_result_content)
                        }
                        await self.store.add_message(self.session_id, tool_msg_dict)
                        lc_messages.append(ToolMessage(
                            tool_call_id=tool_id,
                            content=str(tool_result_content),
                            name=tool_name
                        ))

                    # Loop continues to get next response from LLM (using updated lc_messages)
                else:
                    # No tool calls, we are done
                    await self.store.add_message(self.session_id, ai_msg_dict)
                    yield f"data: {json.dumps({'end': True})}\n\n"
                    break

        except Exception as e:
            logger.error(f"Error in generation: {e}", exc_info=True)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
