from app.services.code_execution.base_handler_factory import BaseFileHandler
import pandas as pd

class CSVHandler(BaseFileHandler):
    def read_file(self, filepath):
        return pd.read_csv(filepath)
    
    def get_file_extensions(self) -> list:
        return ['.csv']