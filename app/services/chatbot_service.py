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
        self.llm_with_tools = self.llm.bind_tools(self.tools, strict=True)


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
            # 1. Load History & metadata for prompt only
            stored_msgs = await self.store.get_messages(self.session_id)

            # 3. Prepare User Message
            user_msg = {"role": "user", "content": query}
            await self.store.add_message(self.session_id, user_msg)
            stored_msgs.append(user_msg)
            
            # 4. Prepare LangChain Messages
            lc_messages = [SystemMessage(content=self.system_prompt)] + self._convert_to_langchain_messages(stored_msgs)

            # 5. Main Loop (for tool calls)
            while True:
                accumulated_msg = None
                
                async for chunk in self.llm_with_tools.astream(lc_messages):
                    if accumulated_msg is None:
                        accumulated_msg = chunk
                    else:
                        accumulated_msg += chunk
                    
                    if chunk.content:
                         yield f"data: {json.dumps({'content': chunk.content}, ensure_ascii=False)}\n\n"
                
                if not accumulated_msg:
                    break
                
                # Store Assistant Message
                ai_msg_dict = {
                    "role": "assistant",
                    "content": accumulated_msg.content,
                }
                
                if accumulated_msg.tool_calls:
                    tool_calls_data = []
                    tasks = []
                    task_ids = []

                    for tc in accumulated_msg.tool_calls:
                        tool_name = tc["name"]
                        tool_args = tc["args"]
                        tool_id = tc["id"]

                        tool_calls_data.append({
                            "id": tool_id,
                            "type": "function",
                            "function": {
                                "name": tool_name,
                                "arguments": json.dumps(tool_args) 
                            }
                        })
                        tasks.append(self.tool_executor.execute(
                            tool_name, 
                            json.dumps(tool_args), 
                            self.session_id,
                            self.store
                        ))
                        task_ids.append({"tool_id": tool_id, "tool_name": tool_name, "tool_args": tool_args})
                    
                    ai_msg_dict["tool_calls"] = tool_calls_data
                    
                    await self.store.add_message(self.session_id, ai_msg_dict)
                    lc_messages.append(accumulated_msg)
                    
                    # 3. Parallel Execution: Run all tools at once
                    logger.info(f"Invoking {len(tasks)} tools in parallel: {[m['tool_name'] for m in task_ids]}")
                    tool_results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    for idx, tool_result in enumerate(tool_results):
                        tool_id = task_ids[idx]["tool_id"]
                        tool_name = task_ids[idx]["tool_name"]
                        if isinstance(tool_result, Exception):
                            tool_result_content = f"Error executing tool {tool_name}: {str(tool_result)}"
                        else:
                            tool_result_content = tool_result
                        
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
