from abc import ABC, abstractmethod
from typing import List
from app import logger
from app.core.config import Config
import json


class BaseRAGPipeline(ABC):
    """
    Abstract base class for RAG pipelines.
    Implementations must define embedding and reranking strategies.
    """
    index = None
    
    def __init__(self):
        self.config = Config()
    
    @abstractmethod
    def get_doc_embed_model(self):
        """Return the embedding model for document indexing"""
        pass
    
    @abstractmethod
    def get_query_embed_model(self):
        """Return the embedding model for query retrieval"""
        pass
    
    @abstractmethod
    def get_reranker(self):
        """Return the reranker model"""
        pass
    
    async def _get_corpus_data(self, questions: List[str], user_query: str) -> list:
        """
        Retrieve top-k relevant context chunks for a question or list of questions.
        """
        try:
            if BaseRAGPipeline.index is None:
                raise RuntimeError("Index not initialized")

            import asyncio
            from llama_index.core import QueryBundle
            from llama_index.core.schema import MetadataMode
            
            retriever = BaseRAGPipeline.index.as_retriever(
                similarity_top_k=self.config.TOP_K, 
                embed_model=self.get_query_embed_model(),
            )
            sem = asyncio.Semaphore(getattr(self.config, "MAX_CONCURRENT_QUERIES", 8))
            
            async def _retrieve_and_rerank(q: str):
                async with sem:
                    results = await retriever.aretrieve(q)
                    return results
            
            tasks = [asyncio.create_task(_retrieve_and_rerank(q)) for q in questions]
            all_results = await asyncio.gather(*tasks)
            flattened_results = [item for sublist in all_results for item in sublist]
            
            if not flattened_results:
                logger.warning("No results retrieved from RAG index.")
                return []
                
            # 1. Broad deduplication
            unique_results = await self._remove_duplicates(flattened_results)
            
            # 2. Precise Global Reranking against the rephrased user query
            final_results = await self._global_reranker(unique_results, user_query)
            
            import json
            return [
                {
                    "content": n.get_content(MetadataMode.NONE),
                    "id": n.node.id_,
                    "title": n.node.metadata.get("title", ""),
                    "pages": json.loads(n.node.metadata.get("pages", "[]")),
                    "bboxes": json.loads(n.node.metadata.get("bboxes", "[]")),
                    "score": n.score,
                }
                for n in final_results
            ]

        except Exception as e:
            logger.error(f"Error retrieving corpus data: {e}", exc_info=True)
            raise

    async def _remove_duplicates(self, content: list):
        """
        Deduplicates results and keeps the highest scoring chunks.
        """
        try:
            import hashlib
            from llama_index.core.schema import MetadataMode
            
            seen_hashes = set()
            unique_docs = []

            for doc in content:
                content_hash = hashlib.md5(doc.get_content(MetadataMode.NONE).encode('utf-8')).hexdigest()
                
                if content_hash not in seen_hashes:
                    unique_docs.append(doc)
                    seen_hashes.add(content_hash)
            
            return unique_docs

        except Exception as e:
            logger.error(f"Error in deduplication: {e}", exc_info=True)
            raise

    async def _global_reranker(self, content: list, user_query: str):
        """
        Final high-precision reranking using the reranker.
        """
        try:
            if not content:
                return []
            
            import asyncio
            from llama_index.core import QueryBundle
            
            filtered_nodes = []
            reranked_nodes = await asyncio.to_thread(
                self.get_reranker().postprocess_nodes, 
                content, 
                QueryBundle(query_str=user_query)
            )
            
            if not reranked_nodes:
                return []
            
            max_score = reranked_nodes[0].score
            
            # Different rerankers use different score ranges:
            # - Cohere: 0 to 1 (positive)
            # - FlagEmbedding: can be negative
            if max_score > 0:
                # Positive scores: use 10% of max with 0.01 floor
                threshold = max(max_score * 0.2, 0.01)
            else:
                threshold = max(max_score * 1.8, -10)
            
            for node in reranked_nodes:
                if node.score >= threshold:
                    filtered_nodes.append(node)
            
            logger.info(f"Reranking filtered: {len(content)} → {len(reranked_nodes)} → {len(filtered_nodes)} (threshold: {threshold:.4f})")

            return filtered_nodes
        
        except Exception as e:
            logger.error(f"Error in global reranker: {e}", exc_info=True)
            return content[:self.config.TOP_N]  # Fallback to top-k if reranking fails

    async def _load_index(self):
        """Load the existing index from disk without rebuilding."""
        try:
            import chromadb
            from llama_index.vector_stores.chroma import ChromaVectorStore
            from llama_index.core import VectorStoreIndex
            
            chroma_client = chromadb.PersistentClient(path=self.config.INDEX_DIR)
            chroma_collection = chroma_client.get_or_create_collection(self.config.COLLECTION_NAME)
            
            if chroma_collection.count() == 0:
                logger.warning("No existing index found on disk. RAG will not work until files are ingested.")
                BaseRAGPipeline.index = None
                return

            # Check embedding dimension compatibility
            current_embed_dim = len(self.get_doc_embed_model().get_text_embedding("test"))
            stored_metadata = chroma_collection.get(limit=1, include=["embeddings"])
            
            if stored_metadata["embeddings"] is not None and len(stored_metadata["embeddings"]) > 0:
                stored_dim = len(stored_metadata["embeddings"][0])
                
                if current_embed_dim != stored_dim:
                    logger.warning(
                        f"Embedding dimension mismatch: Current model uses {current_embed_dim}D, "
                        f"but stored index uses {stored_dim}D. Rebuilding index automatically..."
                    )
                    await self._build_index()
                    return

            vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
            BaseRAGPipeline.index = VectorStoreIndex.from_vector_store(
                vector_store, embed_model=self.get_doc_embed_model()
            )
            logger.info(f"Successfully loaded RAG index with {chroma_collection.count()} vectors.")
        except Exception as e:
            logger.error(f"Failed to load existing RAG index: {e}")
            BaseRAGPipeline.index = None

    async def _build_index(self):
        """Wipe and recreate the RAG index from source_files/."""
        try:
            import asyncio
            import chromadb
            from llama_index.core import Document, StorageContext, VectorStoreIndex
            from llama_index.vector_stores.chroma import ChromaVectorStore
            from llama_index.core.node_parser import SemanticSplitterNodeParser
            from app.services.parser import FileDataProvider
            from llama_index.core.node_parser import SentenceSplitter
            from app.services.rag_service.chunking_service import ChunkingService

            nodes = []
            logger.info("Starting full RAG index rebuild...")
            
            # 1. Clear existing storage
            chroma_client = chromadb.PersistentClient(path=self.config.INDEX_DIR)
            try:
                chroma_client.delete_collection(self.config.COLLECTION_NAME)
            except:
                logger.warning("Failed to delete existing collection. Proceeding with rebuild.")
            
            chroma_collection = chroma_client.get_or_create_collection(self.config.COLLECTION_NAME)
            vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
            storage_context = StorageContext.from_defaults(vector_store=vector_store)

            # 2. Parse all files from DATA_DIR
            def get_docs_sync():
                return list(FileDataProvider(self.config.DATA_DIR).fetch_documents())

            raw_documents = await asyncio.to_thread(get_docs_sync)
            documents: List[Document] = []
            pdf_docs = []
            
            for data in raw_documents:
                metadata = data.get("metadata", {}).copy()
                for key, value in metadata.items():
                    if isinstance(value, (list, dict)):
                        metadata[key] = json.dumps(value)
                
                if "page_data" in data:
                    pdf_docs.append({
                        "id": data.get("id"),
                        "title": data.get("title"),
                        "page_data": data.get("page_data", {}),
                        "metadata": metadata,

                    })
                else:
                    doc = Document(
                        text=data["content"], 
                        id_=data.get("id"), 
                        metadata=metadata,
                        excluded_embed_metadata_keys=["bboxes", "pages", "file_type", "title"],
                        excluded_llm_metadata_keys=["bboxes", "pages", "file_type"],
                    )
                    documents.append(doc)

            if not documents and not pdf_docs:
                logger.warning("No documents found in source_files/. Index will be empty.")
                BaseRAGPipeline.index = None
                return
            
            if pdf_docs:
                from llama_index.core.schema import TextNode
                chunking_service = ChunkingService()

                for doc in pdf_docs:
                    chunks = chunking_service.chunk_pdf_elements(
                        pdf_page_data=doc["page_data"],
                        doc_id=doc["id"],
                        doc_title=doc["title"]
                    )
                    for idx, chunk  in enumerate(chunks):
                        chunk_metadata = {
                            **doc["metadata"],
                            **chunk["metadata"]
                        }
            
                        # Convert any remaining lists/dicts to JSON strings
                        for key, value in chunk_metadata.items():
                            if isinstance(value, (list, dict)):
                                chunk_metadata[key] = json.dumps(value)
                                    
                        node = TextNode(
                            text=chunk["content"],
                            id_=f"{doc.get('id', '')}_c{idx}",
                            metadata=chunk_metadata,
                            excluded_embed_metadata_keys=["bboxes", "pages", "file_type", "title"],
                            excluded_llm_metadata_keys=["bboxes", "pages", "file_type"],
                        )
                        nodes.append(node)
            
            other_docs = [
                d for d in documents
                if d.metadata.get("file_type") != "pdf"
            ]
            if other_docs:
                semantic_splitter = SentenceSplitter(
                    chunk_size=self.config.CHUNK_SIZE,
                    chunk_overlap=self.config.CHUNK_OVERLAP,
                )
                
                logger.info("Splitting documents and assigning bounding boxes to chunks...")
                split_nodes = await asyncio.to_thread(semantic_splitter.get_nodes_from_documents, other_docs)
                nodes.extend(split_nodes)   

            BaseRAGPipeline.index = VectorStoreIndex(
                nodes,
                storage_context=storage_context,
                embed_model=self.get_doc_embed_model(),
                show_progress=True
            )

            logger.info(f"RAG index rebuilt successfully with {len(nodes)} chunks.")
        except Exception as e:
            logger.error(f"Error during RAG index rebuild: {e}", exc_info=True)
            BaseRAGPipeline.index = None
 