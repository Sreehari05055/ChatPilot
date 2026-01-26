import os
from app.services.parser.base_parser import BaseParser
from app import logger


class TextExtractor(BaseParser):
    """
    Extracts text content from TXT files.
    """
    def get_file_extensions(self):
        return ['.txt']
    
    def extract(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                text = f.read()
            
            return {
                "content": self.clean_for_embeddings(text),
                "metadata": {
                    "title": os.path.basename(filepath),
                    "file_type": "text",
                    "source": filepath
                }
            }
        except Exception as e:
            logger.exception(f"Text extraction failed for %s: %s", filepath, e)
            return None