import os
from docling.document_converter import DocumentConverter, WordFormatOption
from docling.datamodel.base_models import InputFormat
from app.services.parser.base_parser import BaseParser
from app.core.hardware import HardwareDetector
from app import logger

class DocxExtractor(BaseParser):
    """
    Extracts text content from DOCX files using Docling with hardware acceleration.
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
        
        self.converter = DocumentConverter(
            format_options={
                InputFormat.DOCX: WordFormatOption(pipeline_options=pipeline_options)
            }
        )

    def get_file_extensions(self):
        return ['.docx']
    
    def extract(self, filepath):
        try:
            logger.info(f"Extracting DOCX with Docling: {filepath}")
            result = self.converter.convert(filepath)
            md_text = result.document.export_to_markdown()
            
            if not md_text or not md_text.strip():
                return None
            
            metadata = {
                "title": result.document.name or os.path.basename(filepath),
                "file_type": "docx",
                "source": filepath
            }
            
            return {
                "content": self.clean_for_embeddings(md_text),
                "metadata": metadata
            }
        except Exception as e:
            logger.error(f"Docling DOCX extraction failed for {filepath}: {e}", exc_info=True)
            return None
