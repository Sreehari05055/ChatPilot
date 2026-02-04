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
        'how did they solve the nested loop problem', 
        'what is blacklisting', 
    ]
    user_query = "Provide information on blacklisting and nestedloop concepts."
    print(f"🔍 Testing 'get_info' with keywords: {keywords}")
    
    try:
        # get_info returns a dict with 'context_text' and 'sources'
        result = await rag_service.get_info(keywords, user_query)
        
        print("\n✅ RAG Retrieval Result:")
        print("-" * 50)
        if result:
            print("Context Text:")
            print(result['context_text'])
            print(f"\n📊 Retrieved {len(result['sources'])} sources")
            for i, source in enumerate(result['sources'][:3], 1):
                print(f"\n[{i}] Doc: {source['doc_id']}, Page: {source.get('page_label', 'N/A')}, Score: {source.get('score', 0.0):.4f}")
        else:
            print("No result returned")
        print("-" * 50)
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        logger.error(f"RAG Test failed: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(test_get_info())
