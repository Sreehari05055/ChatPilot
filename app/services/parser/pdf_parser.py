import os
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from app.services.parser.base_parser import BaseParser
from app.core.hardware import HardwareDetector
from app import logger

class PDFExtractor(BaseParser):
    """
    Extracts text content from PDF files using Docling for high-fidelity layout preservation.
    """
    def __init__(self):
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        
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
            logger.info(f"Extracting PDF with Docling (+Page & BBox): {filepath}")
            result = self.converter.convert(filepath)
            doc_obj = result.document
            
            from collections import defaultdict
            page_data = defaultdict(lambda: {"md": [], "bboxes": []})
            
            # Iterate through all elements (Text, Tables, Headers, etc.)
            for element, _level in doc_obj.iterate_items():
                if not element.prov:
                    continue
                
                prov = element.prov[0]
                page_no = prov.page_no
                element_md = ""
                
                # 1. Extract content based on element type
                if element.__class__.__name__ == 'PictureItem':
                    # OCR extraction optimized with generator expression
                    annots = getattr(element, "annotations", [])
                    element_md = " ".join(a.text for a in annots if hasattr(a, "text")).strip()
                    if not element_md:
                        caption = getattr(element, "caption_text", None)
                        if caption:
                            try:
                                element_md = caption(doc_obj) if callable(caption) else str(caption)
                            except: pass
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
                
                # 2. Validation and cleaning
                element_md = str(element_md or "").strip()
                if not element_md:
                    continue
                    
                page_data[page_no]["md"].append(element_md)
                
                # 3. Store bounding box for highlighting
                if prov.bbox:
                    page_data[page_no]["bboxes"].append({
                        "box": prov.bbox.as_tuple(),
                        "text_snippet": element_md
                    })

            if not page_data:
                logger.warning(f"Docling extracted empty content from {filepath}")
                return None

            segments = []
            doc_title = doc_obj.name or os.path.basename(filepath)
            
            for page_no in sorted(page_data.keys()):
                page_markdown = "\n\n".join(page_data[page_no]["md"])
                if not page_markdown.strip():
                    continue
                
                segments.append({
                    "content": self.clean_for_embeddings(page_markdown),
                    "metadata": {
                        "title": doc_title,
                        "page_label": page_no,
                        "bboxes": page_data[page_no]["bboxes"],
                        "file_type": "pdf",
                        "source": filepath
                    }
                })
                
            return segments
            
        except Exception as e:
            logger.error(f"Docling extraction failed for {filepath}: {e}", exc_info=True)
            return None

