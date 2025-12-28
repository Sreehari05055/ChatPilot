import re
from typing import List
import ftfy
from abc import ABC, abstractmethod
from cleantext import clean

class BaseParser(ABC):
    """
    Base class for all document parsers. Provides shared cleaning utilities.
    """
    @abstractmethod
    def get_file_extensions(self) -> List[str]:
        """Return supported file extensions (lowercase, with dot)."""
        pass
    
    @staticmethod
    def clean_markdown(md: str) -> str:
        # Remove markdown emphasis
        md = re.sub(r"\*\*(.*?)\*\*", r"\1", md)
        md = re.sub(r"_(.*?)_", r"\1", md)
        # Remove excessive hashes if any
        md = re.sub(r"#+\s*", "", md)
        # Normalize bullets
        md = re.sub(r"^\s*[-*]\s+", "", md, flags=re.M)
        # Normalize whitespace
        md = re.sub(r"\n{3,}", "\n\n", md)
        return md.strip()

    @staticmethod
    def clean_for_embeddings(text: str) -> str:
        # 1. Fix broken Unicode / encoding
        md_text = ftfy.fix_text(text)
        # 2. Structural cleanup (safe defaults)
        text = clean(
            md_text,
            fix_unicode=False,   # already handled by ftfy
            to_ascii=False,
            lower=False,
            no_line_breaks=False,
            no_urls=False,
            no_emails=False,
            no_phone_numbers=False,
            no_numbers=False,
            no_punct=False,
        )
        # 3. Light adaptive normalization
        text = re.sub(r"\n{4,}", "\n\n", text)
        text = re.sub(r"[ \t]{2,}", " ", text)
        return text.strip()
