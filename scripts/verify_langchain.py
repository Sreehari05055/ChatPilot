import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import asyncio
from app.services.langchain_handler.langchain_service import LangChainService
from app.services.langchain_handler.tool_definitions import get_tool_schemas
from langchain_core.messages import HumanMessage
from app.core.config import Config

async def main():
    print("Verifying LangChain setup...")
    
    # Test 1: Get LLM
    try:
        llm = LangChainService.get_llm(provider=Config.LLM_PROVIDER) # Or config.LLM_PROVIDER
        print(f"✅ Successfully initialized LLM: {llm}")
    except Exception as e:
        print(f"❌ Failed to initialize LLM: {e}")
        return

    # Test 2: Bind Tools
    try:
        tools = get_tool_schemas()
        llm_with_tools = llm.bind_tools(tools)
        print(f"✅ Successfully bound {len(tools)} tools.")
    except Exception as e:
        print(f"❌ Failed to bind tools: {e}")
        return

    # Test 3: Simple Invocation
    try:
        print("Testing simple invocation...")
        response = await llm.ainvoke([HumanMessage(content="Hello, world!")])
        print(f"✅ Response: {response.content}")
        pass 
    except Exception as e:
        print(f"❌ Failed invocation: {e}")

if __name__ == "__main__":
    asyncio.run(main())
