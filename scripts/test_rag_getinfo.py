import asyncio
import sys
import os

# Add the project root to sys.path so we can import 'app'
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.services.rag_service.rag_execution_service import RAGExecutionService
from app import logger

async def test_get_info():
    print("🚀 Initializing RAG Execution Service...")
    rag_service = RAGExecutionService()
    
    # Initialize the index (load from storage)
    print("📂 Loading index...")
    await rag_service.init_index()
    
    keywords = [
        'college students', 
        'graduates', 
    ]
    user_query = "Provide information on college students and graduates numbers"
    print(f"🔍 Testing 'get_info' with keywords: {keywords}")
    
    try:
        # get_info returns a formatted string (though currently the user has commented out the return)
        # But it also prints the items inside now based on the user's latest change.
        result = await rag_service.get_info(keywords, user_query)
        
        print("\n✅ RAG Retrieval Result:")
        print("-" * 50)
        if result:
            print(result)
        else:
            print("No result returned (check if return statement is commented out in rag_execution_service.py)")
        print("-" * 50)
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        logger.error(f"RAG Test failed: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(test_get_info())
