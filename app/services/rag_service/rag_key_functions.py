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
from llama_index.postprocessor.cohere_rerank import CohereRerank
from fastembed.rerank.cross_encoder import TextCrossEncoder
from llama_index.core import QueryBundle
from llama_index.core.schema import MetadataMode
from llama_index.core import Settings
from llama_index.embeddings.cohere import CohereEmbedding

config = Config()
class RAGPipeline:
    index = None
    def __init__(self):

        self.doc_embed_model = CohereEmbedding(
            api_key=Config.COHERE_API_KEY,
            model_name="embed-english-v3.0",
            input_type="search_document",
            embedding_type="float",
        )

        # 🔹 Query embeddings (RETRIEVAL ONLY)
        self.query_embed_model = CohereEmbedding(
            api_key=Config.COHERE_API_KEY,
            model_name="embed-english-v3.0",
            input_type="search_query",
            embedding_type="float",
        )

        # 🔹 High-precision reranker
        self.reranker = CohereRerank(
            api_key=Config.COHERE_API_KEY,
            model="rerank-english-v3.0",
            top_n=5,
        )

    async def _get_corpus_data(self, questions: List[str], user_query: str) -> list:
        """
        Retrieve top-k relevant context chunks for a question or list of questions.
        """
        try:
            if RAGPipeline.index is None:
                raise RuntimeError("Index not initialized")

            retriever = RAGPipeline.index.as_retriever(similarity_top_k=config.TOP_K, 
                                                       embed_model=self.query_embed_model,
)
            sem = asyncio.Semaphore(getattr(config, "MAX_CONCURRENT_QUERIES", 8))
            
            async def _retrieve_and_rerank(q:str) -> List[str]:
                async with sem:
                    results =  await retriever.aretrieve(q)
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
            
            return [
                {
                    "content": n.get_content(MetadataMode.NONE),
                    "id": n.node.id_,
                    "title": n.node.metadata.get("title", ""),
                    "doc_id": n.node.metadata.get("doc_id", ""),
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
        
        :param content: List of document dictionaries with 'id' and 'score' keys.
        :return: List of top-k unique document dictionaries.
        """
        try:
            import hashlib
            seen_hashes = set()
            unique_docs = []

            for doc in content:
                # Deduplicate by content hash to handle identical text with different IDs
                content_hash = hashlib.md5(doc.get_content(MetadataMode.NONE).encode('utf-8')).hexdigest()
                
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
            filtered_nodes = []
            reranked_nodes = await asyncio.to_thread(
                self.reranker.postprocess_nodes, 
                content, 
                QueryBundle(query_str=user_query)
            )
            max_score = reranked_nodes[0].score if reranked_nodes else 0.0
            threshold = max_score * 0.1

            for node in reranked_nodes:
                if node.score >= threshold:
                    filtered_nodes.append(node)

            return filtered_nodes
        
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
                vector_store, embed_model=self.doc_embed_model
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
                max_chunk_size=config.CHUNK_SIZE,
            )
            
            RAGPipeline.index = VectorStoreIndex.from_documents(
                documents,
                storage_context=storage_context,
                embed_model=self.doc_embed_model,
                transformations=[semantic_splitter],
                show_progress=True
            )

            logger.info(f"RAG index rebuilt successfully with {len(documents)} documents.")
        except Exception as e:
            logger.error(f"Error during RAG index rebuild: {e}", exc_info=True)
            RAGPipeline.index = None