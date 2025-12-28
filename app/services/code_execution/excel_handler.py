from app.services.code_execution.base_handler_factory import BaseFileHandler
import pandas as pd

class ExcelHandler(BaseFileHandler):
    def read_file(self, filepath):
        return pd.read_excel(filepath)

    def get_file_extensions(self) -> list:
        return ['.xlsx', '.xls']