import asyncio
import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.services.rag_service.rag_factory import RAGProviderFactory
from app.services.rag_service.base_rag_pipeline import BaseRAGPipeline

async def test_direct_retrieval():
    print("🔍 Testing direct retrieval (before reranking)...")
    
    # Get the pipeline
    pipeline = RAGProviderFactory.get_provider()
    
    # Load index
    await pipeline._load_index()
    
    if BaseRAGPipeline.index is None:
        print("❌ Index not loaded!")
        return
    
    print("✅ Index loaded")
    
    # Direct retrieval without going through get_corpus_data
    retriever = BaseRAGPipeline.index.as_retriever(
        similarity_top_k=5,
        embed_model=pipeline.get_query_embed_model()
    )
    
    test_query = "blacklisting nestedloop"
    print(f"\n📝 Query: {test_query}")
    
    results = await retriever.aretrieve(test_query)
    
    print(f"\n✅ Retrieved {len(results)} results BEFORE reranking:")
    for i, node in enumerate(results[:3], 1):
        print(f"\n[{i}] Score: {node.score:.4f}")
        print(f"    Content: {node.get_content()[:200]}...")
    
    # Now test with reranking
    print("\n" + "="*80)
    print("Testing WITH reranking...")
    
    from llama_index.core import QueryBundle
    reranker = pipeline.get_reranker()
    
    try:
        reranked = await asyncio.to_thread(
            reranker.postprocess_nodes,
            results,
            QueryBundle(query_str=test_query)
        )
        
        print(f"\n✅ After reranking: {len(reranked)} results")
        for i, node in enumerate(reranked[:3], 1):
            print(f"\n[{i}] Score: {node.score:.4f}")
            print(f"    Content: {node.get_content()[:200]}...")
            
    except Exception as e:
        print(f"\n❌ Reranking FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_direct_retrieval())
