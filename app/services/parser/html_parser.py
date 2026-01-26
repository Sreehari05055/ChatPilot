import os
from docling.document_converter import DocumentConverter, HTMLFormatOption
from docling.datamodel.base_models import InputFormat
from app.services.parser.base_parser import BaseParser
from app.core.hardware import HardwareDetector
from app import logger

class HTMLParser(BaseParser):
    """
    Extracts structured text content from HTML files using Docling with hardware acceleration.
    """
    def __init__(self):
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        
        # 1. Define HTML-specific logic (No OCR needed for native text)
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = True
        
        # 2. Inject global hardware acceleration
        hw_config = HardwareDetector.get_runtime_config()
        pipeline_options.accelerator_options = hw_config["accelerator_options"]
        
        self.converter = DocumentConverter(
            format_options={
                InputFormat.HTML: HTMLFormatOption(pipeline_options=pipeline_options)
            }
        )

    def get_file_extensions(self):
        return ['.html', '.htm']
    
    def extract(self, filepath):
        try:
            logger.info(f"Extracting HTML with Docling: {filepath}")
            result = self.converter.convert(filepath)
            
            # Export to markdown
            md_text = result.document.export_to_markdown()
            
            if not md_text or not md_text.strip():
                logger.warning(f"Docling extracted empty content from {filepath}")
                return None
            
            # Extract metadata
            metadata = {
                "title": result.document.name or os.path.basename(filepath),
                "file_type": "html",
                "source": filepath
            }
            
            # Clean content while preserving structural markdown
            cleaned_content = self.clean_for_embeddings(md_text)
            
            return {
                "content": cleaned_content,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"Docling HTML extraction failed for {filepath}: {e}", exc_info=True)
            return None
