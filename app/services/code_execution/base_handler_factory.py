from abc import ABC, abstractmethod
from typing import Dict
import pandas as pd
from app import logger
import os

class BaseFileHandler(ABC):
    @abstractmethod
    def read_file(self, filepath: str) -> pd.DataFrame:
        pass
    
    @abstractmethod
    def get_file_extensions(self) -> list:
        """
        Return list of supported file extensions.
        Example: ['.csv'] or ['.xlsx', '.xls']
        """
        pass

    def analyze_file(self, filepath: str) -> Dict:
        """
        Analyze file and extract metadata.
        Common implementation for all file types.
        """
        try:
            df = self.read_file(filepath)
            
            sample_rows = pd.concat([
                df.sample(n=3, random_state=42),   # random from whole DF
                df.sample(n=3, random_state=7),    # different part
                df.sample(n=4, random_state=21)    # different part
            ])
            
            sample_dicts = sample_rows.to_dict(orient="records")

            metadata = {
                'filename': filepath,
                'shape': df.shape,
                'columns': df.columns.tolist(),
                'dtypes': {col: str(dtype) for col, dtype in df.dtypes.items()},
                'numeric_columns': df.select_dtypes(include=['number']).columns.tolist(),
                'categorical_columns': df.select_dtypes(include=['object']).columns.tolist(),
                'sample_data': sample_dicts,
                'has_nulls': df.isnull().any().any(),
            }
            
            logger.info(f"Analyzed {filepath}: {metadata['shape']} rows/cols")
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to analyze {filepath}: {e}")
            raise
        
    @staticmethod
    def clean_code_block(code: str) -> str:
        """Remove markdown-style code fences from GPT output."""
        code = code.strip()
        if code.startswith("```"):
            parts = code.split("```")
            if len(parts) >= 2:
                inner = parts[1]
                if inner.startswith("python"):
                    inner = inner[len("python"):].strip()
                code = inner
        return code.strip()