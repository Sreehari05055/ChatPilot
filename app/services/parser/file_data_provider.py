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

                if not result or not isinstance(result, dict):
                    continue
                
                content = result.get("content", "")
                metadata = result.get("metadata", {})
                
                if not content or not content.strip():
                    continue
                
                yield {
                    "id": doc_id,
                    "title": metadata.get("title", title),
                    "content": content,
                    "metadata": metadata
                }

            except ValueError:
                continue  
            except Exception as e:
                logger.exception(f"Error reading {filename}: {e}")
                continue