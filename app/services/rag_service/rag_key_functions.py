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
            top_n=3
        )
    async def _get_corpus_data(self, questions: Union[str, List[str]]) -> list:
        """
        Retrieve top-k relevant context chunks for a question or list of questions using LlamaIndex.

        If `questions` is a string, returns a list of context chunks for that question.
        If `questions` is a list of strings, returns a list where each element is the
        list of context chunks for the corresponding question.
        """
        try:
            if RAGPipeline.index is None:
                raise RuntimeError("Index not initialized")

            retriever = RAGPipeline.index.as_retriever(similarity_top_k=config.TOP_K)

            single_input = isinstance(questions, str)
            question_list = [questions] if single_input else questions

            sem = asyncio.Semaphore(getattr(config, "MAX_CONCURRENT_QUERIES", 8))
            
            async def _retrieve_and_rerank(q:str) -> List[str]:
                async with sem:
                    if hasattr(retriever, "aretrieve"):
                        results = await retriever.aretrieve(q)
                    else:
                        # Fallback for sync-only retriever
                        results = await asyncio.to_thread(retriever.retrieve, q)

                    query_bundle = QueryBundle(q)
                    reranked_nodes = await asyncio.to_thread(
                        self.reranker.postprocess_nodes, results, query_bundle=query_bundle
                    )
                    return [
                        item.node.get_content(metadata_mode=MetadataMode.LLM)
                        for item in reranked_nodes
                    ]
            tasks = [asyncio.create_task(_retrieve_and_rerank(q)) for q in question_list]
            all_results = await asyncio.gather(*tasks)

            return all_results[0] if single_input else all_results

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
                RAGPipeline.index = VectorStoreIndex.from_vector_store(
                    vector_store, embed_model=self.embed_model
                )
                refreshed_ids = RAGPipeline.index.refresh_ref_docs(documents)
                if any(refreshed_ids):
                    logger.info(f"Updated index with changed pages: {refreshed_ids}")
                else:
                    logger.info("No changes detected in files. Index is up to date.")
            else:
                RAGPipeline.index = VectorStoreIndex(
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