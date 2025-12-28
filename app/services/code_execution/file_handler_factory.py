from app.services.code_execution.csv_handler import CSVHandler
from app.services.code_execution.excel_handler import ExcelHandler
import os

class FileHandlerFactory:
    _handlers = [
        CSVHandler(),
        ExcelHandler(),
    ]
 
    @classmethod
    def get_handler(cls, filepath: str):
        ext = os.path.splitext(filepath)[1].lower()
        for handler in cls._handlers:
            if ext in handler.get_file_extensions():
                return handler
        raise ValueError(f"Unsupported file type: {ext}")