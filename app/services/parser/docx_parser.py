from docx import Document
from app.services.parser.base_parser import BaseParser
from app import logger


class DocxExtractor(BaseParser):
    """
    Extracts text content from DOCX files.
    Usage:
        content = DocxExtractor().extract(filepath)
    """
    def get_file_extensions(self):
        return ['.docx']
    
    def extract(self, filepath):
        try:
            doc = Document(filepath)
            text = "\n".join(p.text for p in doc.paragraphs)
            cleaned_text = self.clean_for_embeddings(text)
            return cleaned_text
        except Exception as e:
            logger.exception(f"DOCX extraction failed for %s: %s", filepath, e)
            return ""
