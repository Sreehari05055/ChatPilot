import os
from app.services.parser.base_data_provider import BaseDataProvider
from app.services.parser.parser_factory import ParserFactory


from app import logger

class FileDataProvider(BaseDataProvider):
    def __init__(self, data_dir):
        self.data_dir = data_dir

    def fetch_documents(self):
        for filename in os.listdir(self.data_dir):
            filepath = os.path.join(self.data_dir, filename)
            title = os.path.splitext(filename)[0]
            doc_id = filename  
            try:
                parser = ParserFactory.get_parser(filepath)
                result = parser.extract(filepath)

                if not result:
                    continue
                
                # Handle both single dict and list of segments (for multi-page PDFs)
                if isinstance(result, dict):
                    result = [result]
                
                for idx, segment in enumerate(result):
                    content = segment.get("content", "")
                    metadata = segment.get("metadata", {})
                    
                    if not content or not content.strip():
                        continue
                    
                    # Create unique ID: original_id for single-page, original_id_p1 for multi-page
                    page_label = metadata.get("page_label")
                    segment_id = f"{doc_id}_p{page_label}" if page_label else doc_id
                    
                    yield {
                        "id": segment_id,
                        "title": metadata.get("title", title),
                        "content": content,
                        "metadata": metadata
                    }

            except ValueError:
                continue  
            except Exception as e:
                logger.exception(f"Error reading {filename}: {e}")
                continue