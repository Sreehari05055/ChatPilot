from app.services.parser.base_parser import BaseParser
from app import logger


class TextExtractor(BaseParser):
    """
    Extracts text content from TXT files.
    Usage:
        content = TextExtractor().extract(filepath)
    """
    def get_file_extensions(self):
        return ['.txt']
    
    def extract(self, filepath):
        try:
            # Implement TXT extraction logic using your preferred library
            with open(filepath, 'r', encoding='utf-8') as f:
                text = f.read()
            cleaned_text = self.clean_for_embeddings(text)
            return cleaned_text
        except Exception as e:
            logger.exception(f"Text extraction failed for %s: %s", filepath, e)
            return ""