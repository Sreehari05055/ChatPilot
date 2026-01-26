import os
from app.services.parser.base_parser import BaseParser
from app import logger


class MarkdownExtractor(BaseParser):
    """
    Extracts text content from MARKDOWN files.
    """
    def get_file_extensions(self):
        return ['.md']
    
    def extract(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                md_text = f.read()
            
            cleaned_md_text = self.clean_markdown(md_text)
            cleaned_text_for_embeddings = self.clean_for_embeddings(cleaned_md_text)
            
            return {
                "content": cleaned_text_for_embeddings,
                "metadata": {
                    "title": os.path.basename(filepath),
                    "file_type": "markdown",
                    "source": filepath
                }
            }
        except Exception as e:
            logger.exception(f"Markdown extraction failed for %s: %s", filepath, e)
            return None