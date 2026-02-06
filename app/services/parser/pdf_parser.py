import os
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from app.services.parser.base_parser import BaseParser
from app.core.hardware import HardwareDetector
from app import logger
from app.core.config import Config
from transformers import AutoTokenizer

class PDFExtractor(BaseParser):
    """
    Extracts text content from PDF files using Docling for high-fidelity layout preservation.
    """
    def __init__(self):
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        self.tokenizer = AutoTokenizer.from_pretrained(Config.EMBEDDING_MODEL, model_max_length=int(1e30))
        # 1. Define PDF-specific logic (Layout + OCR + Tables)
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = True
        pipeline_options.do_table_structure = True
        
        # 2. Inject global hardware acceleration
        hw_config = HardwareDetector.get_runtime_config()
        pipeline_options.accelerator_options = hw_config["accelerator_options"]
        
        # Apply batch sizes if high-performance mode is active
        for key, value in hw_config["batch_sizes"].items():
            setattr(pipeline_options, key, value)
        
        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )

    def get_file_extensions(self):
        return ['.pdf']

    def extract(self, filepath):
        try:
            logger.info(f"Extracting PDF with Docling: {filepath}")
            result = self.converter.convert(filepath)
            doc_obj = result.document
            # Always use the actual filename with extension for proper file routing
            doc_title = os.path.basename(filepath)
            
            chunks = []

            def finalize_chunk(chunk):
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

            def new_chunk():
                return {
                    "content": [],
                    "bboxes": [],
                    "pages": set(),
                    "token_count": 0
                }

            def append_element(chunk, text, tokens, page, bbox):
                """Add an element's text and bbox to a chunk."""
                # Account for \n\n join token if not the first element
                if chunk["content"]:
                    chunk["token_count"] += JOIN_TOKEN_COST
                chunk["content"].append(text)
                chunk["token_count"] += tokens
                chunk["pages"].add(page)
                if bbox:
                    chunk["bboxes"].append({
                        "page": page,
                        "box": bbox
                    })

            def split_oversized_element(text, page, bbox):
                """Split a text that exceeds CHUNK_SIZE at sentence/line boundaries."""
                # First, normalize line breaks into spaces to rejoin wrapped sentences
                # Then split by paragraph breaks (\n\n) and sentences (. )
                text = text.replace("\n\n", "<PARA>").replace("\n", " ").replace("<PARA>", "\n\n")
                
                sentences = []
                for para in text.split("\n\n"):
                    for sent in para.split(". "):
                        s = sent.strip()
                        if s:
                            sentences.append(s)
                
                sub_chunk = new_chunk()
                for sent in sentences:
                    sent_tokens = len(self.tokenizer.encode(sent, add_special_tokens=False))
                    join_cost = JOIN_TOKEN_COST if sub_chunk["content"] else 0
                    
                    if sub_chunk["token_count"] + join_cost + sent_tokens > Config.CHUNK_SIZE:
                        if sub_chunk["token_count"] > 0:
                            if bbox:
                                sub_chunk["bboxes"].append({"page": page, "box": bbox})
                            sub_chunk["pages"].add(page)
                            finalize_chunk(sub_chunk)
                        sub_chunk = new_chunk()
                    
                    if sub_chunk["content"]:
                        sub_chunk["token_count"] += JOIN_TOKEN_COST
                    sub_chunk["content"].append(sent)
                    sub_chunk["token_count"] += sent_tokens
                
                # Finalize remaining
                if sub_chunk["token_count"] > 0:
                    if bbox:
                        sub_chunk["bboxes"].append({"page": page, "box": bbox})
                    sub_chunk["pages"].add(page)
                    finalize_chunk(sub_chunk)

            # Account for join tokens ("\n\n" between elements)
            JOIN_TOKEN_COST = len(self.tokenizer.encode("\n\n", add_special_tokens=False))

            current_chunk = new_chunk()

            for element, _level in doc_obj.iterate_items():
                if not element.prov:
                    continue
                
                prov = element.prov[0]
                page_no = prov.page_no
                element_md = ""
                
                # 1. Extract content based on element type
                if element.__class__.__name__ == 'PictureItem':
                    annots = getattr(element, "annotations", [])
                    element_md = " ".join(a.text for a in annots if hasattr(a, "text")).strip()
                    if not element_md:
                        caption = getattr(element, "caption_text", None)
                        if caption:
                            try:
                                element_md = caption(doc_obj) if callable(caption) else str(caption)
                            except: 
                                pass
                else:
                    try:
                        if hasattr(element, 'export_to_markdown'):
                            try:
                                element_md = element.export_to_markdown(doc_obj)
                            except TypeError:
                                element_md = element.export_to_markdown()
                        elif hasattr(element, 'text'):
                            text_attr = element.text
                            element_md = text_attr() if callable(text_attr) else text_attr
                    except:
                        continue
                
                element_md = self.clean_for_embeddings(element_md)
                element_token_count = len(self.tokenizer.encode(element_md, add_special_tokens=False))
                
                if not element_md or element_token_count == 0:
                    continue

                bbox_tuple = prov.bbox.as_tuple() if prov.bbox else None

                # 2. Handle oversized element: split at sentence boundaries
                if element_token_count > Config.CHUNK_SIZE:
                    # Finalize current chunk first
                    if current_chunk["token_count"] > 0:
                        finalize_chunk(current_chunk)
                        current_chunk = new_chunk()
                    
                    split_oversized_element(element_md, page_no, bbox_tuple)
                    continue

                # 3. Check if adding this element would exceed chunk size
                # token_count already includes previous join costs, add one more for this element
                join_cost = JOIN_TOKEN_COST if current_chunk["content"] else 0
                if current_chunk["token_count"] + join_cost + element_token_count > Config.CHUNK_SIZE:
                    finalize_chunk(current_chunk)
                    current_chunk = new_chunk()

                # 4. Add element to current chunk
                append_element(current_chunk, element_md, element_token_count, page_no, bbox_tuple)
                
            # Finalize the last chunk
            if current_chunk["token_count"] > 0:
                finalize_chunk(current_chunk)
            
            if not chunks:
                logger.warning(f"No text content extracted from {filepath}")
                return None
            
            return chunks

        except Exception as e:
            logger.error(f"Docling extraction failed for {filepath}: {e}", exc_info=True)
            return None

