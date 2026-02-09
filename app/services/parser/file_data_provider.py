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
            doc_id = os.path.basename(filepath)

            try:
                parser = ParserFactory.get_parser(filepath)
                raw_data = parser.extract(filepath)

                if not raw_data:
                    continue
                
                if isinstance(raw_data, dict) and "page_data" in raw_data:
                    yield {
                        "id": doc_id,
                        "title": raw_data.get("title", title),
                        "page_data": raw_data.get("page_data", {}),
                        "metadata": raw_data.get("metadata", {})
                    }
                    
                else:
                    if not isinstance(raw_data, list):
                        raw_data = [raw_data]
                
                    for idx, segment in enumerate(raw_data):
                        content = segment.get("content", "")
                        metadata = segment.get("metadata", {})
                        
                        if not content or not content.strip():
                            continue
                        
                        # Generate unique ID for each chunk using the absolute doc id
                        segment_id = f"{doc_id}_c{idx}"

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