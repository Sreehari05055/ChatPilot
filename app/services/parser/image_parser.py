import os
from docling.document_converter import DocumentConverter, ImageFormatOption
from docling.datamodel.base_models import InputFormat
from app.services.parser.base_parser import BaseParser
from app.core.hardware import HardwareDetector
from app import logger
from PIL import Image

class ImageExtractor(BaseParser):
    """
    Extracts text and structured content from image files (OCR) using Docling.
    """
    def __init__(self):
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        
        # 1. Define Image-specific logic (Full OCR)
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = True
        pipeline_options.do_table_structure = True
        
        # 2. Inject global hardware acceleration
        hw_config = HardwareDetector.get_runtime_config()
        pipeline_options.accelerator_options = hw_config["accelerator_options"]
        
        self.converter = DocumentConverter(
            format_options={
                InputFormat.IMAGE: ImageFormatOption(pipeline_options=pipeline_options)
            }
        )

    def get_file_extensions(self):
        return ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']
    
    def extract(self, filepath):
        try:
            try:
                with Image.open(filepath) as img:
                    img.verify()
            except Exception as img_err:
                logger.warning(f"Invalid image file {filepath}: {img_err}")
                return None
            
            logger.info(f"Extracting Image with Docling: {filepath}")
            
            result = self.converter.convert(filepath)
            md_text = result.document.export_to_markdown()
            
            if not md_text or not md_text.strip():
                return None
            
            metadata = {
                "title": os.path.basename(filepath),
                "file_type": "image",
                "source": filepath,
                "mimetype": f"image/{os.path.splitext(filepath)[1].strip('.')}"
            }
            
            return {
                "content": self.clean_for_embeddings(md_text),
                "metadata": metadata
            }
        except Exception as e:
            logger.error(f"Docling Image extraction failed for {filepath}: {e}", exc_info=True)
            return None
