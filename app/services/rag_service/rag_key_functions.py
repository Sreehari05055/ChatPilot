from platform import node
from typing import List
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
#data_provider = get_data_provider(config)

class RAGPipeline:
    def __init__(self):
        self.index = None
        self.embed_model = HuggingFaceEmbedding(model_name=config.EMBEDDING_MODEL_NAME)
        self.reranker = SentenceTransformerRerank(
            model="BAAI/bge-reranker-v2-m3", 
            top_n=3
        )
    async def _get_corpus_data(self, question: str) -> list:
        """
        Retrieve top-k relevant context chunks for a question using LlamaIndex.
        """
        try:
            if self.index is None:
                raise RuntimeError("Index not initialized")

            retriever = self.index.as_retriever(similarity_top_k=config.TOP_K)

            if hasattr(retriever, "aretrieve"):
                results = await retriever.aretrieve(question)
            else:
                # Fallback for sync-only retriever
                results = await asyncio.to_thread(retriever.retrieve, question)
            
            query_bundle = QueryBundle(question)
            reranked_nodes = self.reranker.postprocess_nodes(
                results, query_bundle=query_bundle
            )

            context_chunks = []
            for item in reranked_nodes:
                node = item.node
                content_for_llm = node.get_content(metadata_mode=MetadataMode.LLM)
                context_chunks.append(content_for_llm)

            return context_chunks
        
        except Exception as e:
            logger.error(f"Error retrieving corpus data: {e}", exc_info=True)
            raise

    async def _build_index(self):
        try:

            semantic_splitter = SemanticDoubleMergingSplitterNodeParser.from_defaults(
                initial_threshold=0.5,
                appending_threshold=0.8,
                merging_threshold=0.7,
                max_chunk_size=config.CHUNK_SIZE
            )
            chroma_client = chromadb.PersistentClient(path=config.INDEX_DIR)
            chroma_collection = chroma_client.get_or_create_collection(config.COLLECTION_NAME)
            vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
            
            def get_docs_sync():
                    return list(FileDataProvider(config.DATA_DIR).fetch_documents())

            raw_documents = await asyncio.to_thread(get_docs_sync)
            documents: List[Document] = []
            for data in raw_documents:
                content = data.get("content", "")
                title = data.get("title", "")
                doc_id = data.get("id", None)

                doc = Document(
                    text=content, 
                    id_=doc_id, 
                    metadata={
                        "title": title, 
                        "doc_id": doc_id.split("_chunk")[0]
                    },
                    text_template="SOURCE: {metadata_str}\n---\nCONTENT: {content}",
                    metadata_template="{key}: {value}",
                    metadata_seperator=" | "
                )
                doc.excluded_embed_metadata_keys = ["title", "doc_id"]

                documents.append(doc)

            storage_context = StorageContext.from_defaults(vector_store=vector_store)
            
            if chroma_collection.count() > 0:
                logger.info("Existing index found. Loading from persistent storage.")
                self.index = VectorStoreIndex.from_vector_store(
                    vector_store, embed_model=self.embed_model
                )
                refreshed_ids = self.index.refresh_ref_docs(documents)
                if any(refreshed_ids):
                    logger.info(f"Updated index with changed pages: {refreshed_ids}")
                else:
                    logger.info("No changes detected in files. Index is up to date.")
            else:
                self.index = VectorStoreIndex(
                    documents,
                    storage_context=storage_context,
                    embed_model=self.embed_model,
                    transformations=[semantic_splitter]
                )
                logger.info("Created new RAG index from documents.")

            logger.info("RAG index built and persisted successfully.")
        except Exception as e:
            logger.error(f"Error building RAG index: {e}", exc_info=True)
            self.index = None