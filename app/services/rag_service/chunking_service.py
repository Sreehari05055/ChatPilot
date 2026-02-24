from transformers import AutoTokenizer
from app.core.config import Config
from typing import List
from app import logger

class ChunkingService:
    def __init__(self):
        try:
            # Use tiktoken for OpenAI models to avoid HuggingFace Hub errors
            if "text-embedding-3" in Config.EMBEDDING_MODEL.lower() or "openai" in Config.EMBEDDING_PROVIDER.lower():
                import tiktoken
                self.tokenizer = tiktoken.get_encoding("cl100k_base")
                self.token_mode = "tiktoken"
            elif "cohere" in Config.EMBEDDING_PROVIDER.lower():
                # Cohere uses API-based models; use gpt2 as a close-enough local proxy for chunking
                logger.info("Cohere provider detected. Using 'gpt2' local proxy for token counting.")
                self.token_mode = "transformers"
                self.tokenizer = AutoTokenizer.from_pretrained("gpt2")
            else:
                self.token_mode = "transformers"
                self.tokenizer = AutoTokenizer.from_pretrained(Config.EMBEDDING_MODEL, model_max_length=int(1e30))
        except Exception as e:
            logger.warning(f"Failed to load tokenizer for {Config.EMBEDDING_MODEL}: {e}. Falling back to default 'gpt2'.")
            self.token_mode = "transformers"
            self.tokenizer = AutoTokenizer.from_pretrained("gpt2")
            
        # Standardize joining cost
        if self.token_mode == "tiktoken":
            self.JOIN_TOKEN_COST = len(self.tokenizer.encode("\n\n"))
        else:
            self.JOIN_TOKEN_COST = len(self.tokenizer.encode("\n\n", add_special_tokens=False))
            
        self.CHUNK_SIZE = Config.CHUNK_SIZE


    def chunk_pdf_elements(self, pdf_page_data: dict, doc_id: str, doc_title: str) -> List[dict]:
        """
        Chunk PDF content based on token limits, preserving page and bbox metadata.
        """
        chunks = []
        current_chunk = self._new_chunk()

        for page_no in sorted(pdf_page_data.keys()):
            page_info = pdf_page_data[page_no]

            for element in page_info.get("elements", []):
                text = element.get("content", "")
                tokens = element.get("tokens", 0)
                bbox = element.get("bbox")

                if tokens > self.CHUNK_SIZE:
                    if current_chunk["token_count"] > 0:
                        self._finalize_chunk(current_chunk, chunks, doc_title)
                        current_chunk = self._new_chunk()
                    self._split_oversized_element(text, page_no, bbox, chunks, doc_title)
            
                elif current_chunk["token_count"] + tokens + (self.JOIN_TOKEN_COST if current_chunk["content"] else 0) > self.CHUNK_SIZE:
                    # Finalize current chunk and start a new one
                    self._finalize_chunk(current_chunk, chunks, doc_title)
                    current_chunk = self._new_chunk()
                    self._append_element(current_chunk, text, tokens, page_no, bbox)
                else:
                    # Add element to current chunk
                    self._append_element(current_chunk, text, tokens, page_no, bbox)

        self._finalize_chunk(current_chunk, chunks, doc_title)
        return chunks

    def _finalize_chunk(self, chunk, chunks, doc_title):
        """Save a completed chunk to the chunks list."""
        if chunk["token_count"] == 0:
            return

        chunks.append({
            "content": "\n\n".join(chunk["content"]),
            "metadata": {
                "title": doc_title,
                "pages": sorted(chunk["pages"]),
                "bboxes": chunk["bboxes"],
                "file_type": "pdf"
            }
        })

    def _new_chunk(self):
        return {
            "content": [],
            "bboxes": [],
            "pages": set(),
            "token_count": 0
        }

    def _append_element(self, chunk, text, tokens, page, bbox):
        """Add an element's text and bbox to a chunk."""
        # Account for \n\n join token if not the first element
        if chunk["content"]:
            chunk["token_count"] += self.JOIN_TOKEN_COST
        chunk["content"].append(text)
        chunk["token_count"] += tokens
        chunk["pages"].add(page)
        if bbox:
            chunk["bboxes"].append({
                "page": page,
                "box": bbox
            })

    def _split_oversized_element(self, text: str, page: int, bbox: tuple, chunks: list, doc_title: str):
        """Split a text that exceeds CHUNK_SIZE at sentence/line boundaries."""
        text = text.replace("\n\n", "<PARA>").replace("\n", " ").replace("<PARA>", "\n\n")
        
        sentences = []
        for para in text.split("\n\n"):
            for sent in para.split(". "):
                s = sent.strip()
                if s:
                    sentences.append(s)
        
        sub_chunk = self._new_chunk()
        for sent in sentences:
            if self.token_mode == "tiktoken":
                sent_tokens = len(self.tokenizer.encode(sent))
            else:
                sent_tokens = len(self.tokenizer.encode(sent, add_special_tokens=False))
            
            join_cost = self.JOIN_TOKEN_COST if sub_chunk["content"] else 0
            
            if sub_chunk["token_count"] + join_cost + sent_tokens > self.CHUNK_SIZE:
                if sub_chunk["token_count"] > 0:
                    if bbox:
                        sub_chunk["bboxes"].append({"page": page, "box": bbox})
                    sub_chunk["pages"].add(page)
                    self._finalize_chunk(sub_chunk, chunks, doc_title)
                sub_chunk = self._new_chunk()
            
            if sub_chunk["content"]:
                sub_chunk["token_count"] += self.JOIN_TOKEN_COST
            sub_chunk["content"].append(sent)
            sub_chunk["token_count"] += sent_tokens
        
        # Finalize remaining
        if sub_chunk["token_count"] > 0:
            if bbox:
                sub_chunk["bboxes"].append({"page": page, "box": bbox})
            sub_chunk["pages"].add(page)
            self._finalize_chunk(sub_chunk, chunks, doc_title)
