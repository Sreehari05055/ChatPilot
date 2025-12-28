from typing import List
from app import logger
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core import Document, StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core.node_parser import SimpleNodeParser
import asyncio
from app.core.config import Config
from llama_index.core import GPTVectorStoreIndex
import chromadb
from app.services.data_provider_factory import get_data_provider

config = Config()
data_provider = get_data_provider(config)

class RAGPipeline:
    def __init__(self):
        self.index = None
        self.embed_model = HuggingFaceEmbedding(model_name=config.EMBEDDING_MODEL_NAME)


    def init_index(self):
        self._build_index()


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

            context_chunks = []
            for item in results:
                node = getattr(item, "node", item)
                if hasattr(node, "get_content"):
                    context_chunks.append(node.get_content())
                elif hasattr(node, "get_text"):
                    context_chunks.append(node.get_text())
                else:
                    context_chunks.append(str(node))
            return context_chunks
        except Exception as e:
            logger.error(f"Error retrieving corpus data: {e}", exc_info=True)
            raise

    def _build_index(self):
        try:
            raw_documents = data_provider.fetch_documents()
            documents: List[Document] = []
            for data in raw_documents:
                content = data.get("content", "")
                title = data.get("title", "")
                doc_id = data.get("id", None)
                documents.append(Document(text=content, metadata={"title": title, "id": doc_id}))

            node_parser = SimpleNodeParser.from_defaults(
                chunk_size=config.CHUNK_SIZE,
                chunk_overlap=config.CHUNK_OVERLAP
            )
            nodes = node_parser.get_nodes_from_documents(documents)

            # Use persistent Chroma client
            chroma_client = chromadb.PersistentClient(path=config.INDEX_DIR)
            chroma_collection = chroma_client.get_or_create_collection(config.COLLECTION_NAME)

            vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
            storage_context = StorageContext.from_defaults(vector_store=vector_store)

            self.index = GPTVectorStoreIndex(
                nodes,
                storage_context=storage_context,
                embed_model=self.embed_model,
            )
            # Attempt to explicitly persist Chroma to disk; API varies by chromadb version
            try:
                chroma_client.persist()
            except Exception:
                pass

            logger.info("RAG index built and persisted successfully.")
        except Exception as e:
            logger.error(f"Error building RAG index: {e}", exc_info=True)
            self.index = None