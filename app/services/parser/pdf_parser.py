import os
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from app.services.parser.base_parser import BaseParser
from app.core.hardware import HardwareDetector
from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
from app import logger
from app.core.config import Config
from transformers import AutoTokenizer
from collections import defaultdict

class PDFExtractor(BaseParser):

    """
    Extracts text content from PDF files using Docling for high-fidelity layout preservation.
    """
    def __init__(self):
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.datamodel.pipeline_options import TableStructureOptions, TableFormerMode

        pipeline_options = PdfPipelineOptions()
        hw_config = HardwareDetector.get_runtime_config()
        table_options = TableStructureOptions()
        table_options.mode = TableFormerMode.FAST 

        pipeline_options.do_ocr = False
        pipeline_options.do_table_structure = True
        pipeline_options.table_structure_options = table_options
        pipeline_options.accelerator_options = hw_config["accelerator_options"]
        try:
            if "text-embedding-3" in Config.EMBEDDING_MODEL.lower() or "openai" in Config.EMBEDDING_PROVIDER.lower():
                import tiktoken
                self.tokenizer = tiktoken.get_encoding("cl100k_base")
                self.token_mode = "tiktoken"
            elif "cohere" in Config.EMBEDDING_PROVIDER.lower():
                # Use gpt2 proxy for Cohere to avoid HF errors
                logger.info("Cohere provider detected for PDF extraction. Using 'gpt2' local proxy.")
                self.token_mode = "transformers"
                self.tokenizer = AutoTokenizer.from_pretrained("gpt2")
            else:
                self.token_mode = "transformers"
                self.tokenizer = AutoTokenizer.from_pretrained(Config.EMBEDDING_MODEL, model_max_length=int(1e30))
        except Exception as e:
            logger.warning(f"PDFExtractor failed to load tokenizer for {Config.EMBEDDING_MODEL}: {e}. Falling back to 'gpt2'.")
            self.token_mode = "transformers"
            self.tokenizer = AutoTokenizer.from_pretrained("gpt2")

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
            
            page_data = defaultdict(lambda: {"elements": []})

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
                if self.token_mode == "tiktoken":
                    element_token_count = len(self.tokenizer.encode(element_md))
                else:
                    element_token_count = len(self.tokenizer.encode(element_md, add_special_tokens=False))
                
                if not element_md or element_token_count == 0:
                    continue

                bbox_tuple = prov.bbox.as_tuple() if prov.bbox else None

                page_data[prov.page_no]["elements"].append({
                        "content": element_md,
                        "tokens": element_token_count,
                        "level": _level,  
                        "type": element.__class__.__name__,
                        "bbox": bbox_tuple
                    })
                
            return {
                "page_data": dict(page_data),
                "title": doc_title,
                "metadata": {
                    "file_type": "pdf",
                    "title": doc_title,
                    "source": filepath
            }
            }
        except Exception as e:
            logger.error(f"Docling extraction failed for {filepath}: {e}", exc_info=True)
            return None

