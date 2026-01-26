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
            logger.info(f"Extracting PDF with Docling (+Metadata): {filepath}")
            result = self.converter.convert(filepath)
            
            # Export to markdown
            md_text = result.document.export_to_markdown()
            
            if not md_text or not md_text.strip():
                logger.warning(f"Docling extracted empty content from {filepath}")
                return None
            
            # Extract document-level metadata
            # Docling handles many formats; for PDFs, we look at the 'origin' and 'name'
            metadata = {
                "title": result.document.name or os.path.basename(filepath),
                "page_count": len(result.document.pages) if hasattr(result.document, "pages") else 0,
                "file_type": "pdf",
                "source": filepath
            }
            
            # If docling captured specific origin info, we can add it
            if result.document.origin:
                # 'mimetype' helps identify if it was actually a scan or a digital PDF
                metadata["mimetype"] = result.document.origin.mimetype
            
            # Clean but keep structure
            cleaned_content = self.clean_for_embeddings(md_text)
            
            return {
                "content": cleaned_content,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"Docling extraction failed for {filepath}: {e}", exc_info=True)
            return None

