from platform import node
from typing import List, Union
from app import logger
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core import Document, StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core.node_parser import SemanticDoubleMergingSplitterNodeParser
import asyncio
from app.core.config import Config
from llama_index.core import VectorStoreIndex
import chromadb
from app.services.parser import FileDataProvider
from llama_index.core.postprocessor import SentenceTransformerRerank
from llama_index.core import QueryBundle
from llama_index.core.schema import MetadataMode
from llama_index.core import Settings

config = Config()
class RAGPipeline:
    index = None
    def __init__(self):
        self.embed_model = HuggingFaceEmbedding(model_name=config.EMBEDDING_MODEL_NAME)
        self.reranker = SentenceTransformerRerank(
            model="BAAI/bge-reranker-v2-m3", 
            top_n=10
        )
    async def _get_corpus_data(self, questions: List[str], user_query: str) -> list:
        """
        Retrieve top-k relevant context chunks for a question or list of questions.
        """
        try:
            if RAGPipeline.index is None:
                raise RuntimeError("Index not initialized")

            retriever = RAGPipeline.index.as_retriever(similarity_top_k=config.TOP_K)
            sem = asyncio.Semaphore(getattr(config, "MAX_CONCURRENT_QUERIES", 8))
            
            async def _retrieve_and_rerank(q:str) -> List[str]:
                async with sem:
                    if hasattr(retriever, "aretrieve"):
                        results = await retriever.aretrieve(q)
                    else:
                        results = await asyncio.to_thread(retriever.retrieve, q)

                    return [
                        {
                            "content": item.node.get_content(metadata_mode=MetadataMode.NONE), # Get RAW text here
                            "id": item.node.id_,
                            "title": item.node.metadata.get("title", ""),
                            "doc_id": item.node.metadata.get("doc_id", ""),
                            "score": item.score
                        }
                        for item in results
                    ]

            tasks = [asyncio.create_task(_retrieve_and_rerank(q)) for q in questions]
            all_results = await asyncio.gather(*tasks)
            flattened_results = [item for sublist in all_results for item in sublist]
            
            # 1. Broad deduplication
            unique_results = await self._remove_duplicates(flattened_results)
            
            # 2. Precise Global Reranking against the rephrased user query
            final_results = await self._global_reranker(unique_results, user_query)
            
            return final_results

        except Exception as e:
            logger.error(f"Error retrieving corpus data: {e}", exc_info=True)
            raise

    async def _remove_duplicates(self, content: list):
        """
        Deduplicates results and keeps the highest scoring chunks.
        
        :param content: List of document dictionaries with 'id' and 'score' keys.
        :return: List of top-k unique document dictionaries.
        """
        try:
            import hashlib
            seen_hashes = set()
            unique_docs = []

            for doc in content:
                # Deduplicate by content hash to handle identical text with different IDs
                content_hash = hashlib.md5(doc["content"].encode('utf-8')).hexdigest()
                
                if content_hash not in seen_hashes:
                    unique_docs.append(doc)
                    seen_hashes.add(content_hash)
            
            return unique_docs

        except Exception as e:
            logger.error(f"Error in reciprocal ranker: {e}", exc_info=True)
            raise

    async def _global_reranker(self, content: list, user_query: str):
        """
        Final high-precision reranking using the cross-encoder.
        """
        try:
            if not content:
                return []

            query_bundle = QueryBundle(user_query)
            
            from llama_index.core.schema import NodeWithScore, TextNode
            
            nodes_with_score = [
                NodeWithScore(
                    node=TextNode(
                        text=item["content"], 
                        id_=item["id"], 
                        metadata={"title": item["title"], "doc_id": item["doc_id"]}
                    ),
                    score=item["score"]
                )
                for item in content
            ]

            reranked_nodes = await asyncio.to_thread(
                self.reranker.postprocess_nodes, 
                nodes_with_score, 
                query_bundle=query_bundle
            )
            
            reranked_results = [
                {
                    "content": item.node.get_content(metadata_mode=MetadataMode.LLM),
                    "id": item.node.id_,
                    "title": item.node.metadata.get("title", ""),
                    "doc_id": item.node.metadata.get("doc_id", ""),
                    "score": item.score
                }
                for item in reranked_nodes
            ]

            # Re-sorting just to be absolutely sure, though reranker usually handles this
            return reranked_results
        
        except Exception as e:
            logger.error(f"Error in global reranker: {e}", exc_info=True)
            return content[:config.TOP_K] # Fallback to top-k if reranking fails

    async def _load_index(self):
        """Load the existing index from disk without rebuilding."""
        try:
            chroma_client = chromadb.PersistentClient(path=config.INDEX_DIR)
            chroma_collection = chroma_client.get_or_create_collection(config.COLLECTION_NAME)
            
            if chroma_collection.count() == 0:
                logger.warning("No existing index found on disk. RAG will not work until files are ingested.")
                RAGPipeline.index = None
                return

            vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
            RAGPipeline.index = VectorStoreIndex.from_vector_store(
                vector_store, embed_model=self.embed_model
            )
            logger.info(f"Successfully loaded RAG index with {chroma_collection.count()} vectors.")
        except Exception as e:
            logger.error(f"Failed to load existing RAG index: {e}")
            RAGPipeline.index = None

    async def _build_index(self):
        """Wipe and recreate the RAG index from source_files/."""
        try:
            logger.info("Starting full RAG index rebuild...")
            
            # 1. Clear existing storage
            chroma_client = chromadb.PersistentClient(path=config.INDEX_DIR)
            try:
                chroma_client.delete_collection(config.COLLECTION_NAME)
            except:
                logger.warning("Failed to delete existing collection. Proceeding with rebuild.")
            
            chroma_collection = chroma_client.get_or_create_collection(config.COLLECTION_NAME)
            vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
            storage_context = StorageContext.from_defaults(vector_store=vector_store)

            # 2. Parse all files from DATA_DIR
            def get_docs_sync():
                return list(FileDataProvider(config.DATA_DIR).fetch_documents())

            raw_documents = await asyncio.to_thread(get_docs_sync)
            documents: List[Document] = []
            
            for data in raw_documents:
                doc = Document(
                    text=data.get("content", ""), 
                    id_=data.get("id"), 
                    metadata={
                        "title": data.get("title", ""), 
                        "doc_id": data.get("id", "").split("_chunk")[0]
                    }
                )
                documents.append(doc)

            if not documents:
                logger.warning("No documents found in source_files/. Index will be empty.")
                RAGPipeline.index = None
                return

            # 3. Create fresh index
            semantic_splitter = SemanticDoubleMergingSplitterNodeParser.from_defaults(
                max_chunk_size=config.CHUNK_SIZE
            )
            
            RAGPipeline.index = VectorStoreIndex(
                documents,
                storage_context=storage_context,
                embed_model=self.embed_model,
                transformations=[semantic_splitter]
            )

            logger.info(f"RAG index rebuilt successfully with {len(documents)} documents.")
        except Exception as e:
            logger.error(f"Error during RAG index rebuild: {e}", exc_info=True)
            RAGPipeline.index = None