import os
from app.services.base_data_provider import BaseDataProvider
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

                if isinstance(result, list):  # chunked (HTML)
                    for i, chunk in enumerate(result):
                        if not chunk or not chunk.strip():
                            continue
                        yield {
                            "id": f"{doc_id}_chunk{i+1}",
                            "title": f"{title} (Section {i+1})",
                            "content": chunk,
                        }
                else:
                    if not result or not result.strip():
                        continue
                    yield {
                        "id": doc_id,
                        "title": title,
                        "content": result,
                    }

            except ValueError:
                continue  
            except Exception as e:
                logger.exception(f"Error reading {filename}: {e}")
                continue