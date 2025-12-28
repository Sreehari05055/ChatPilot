import os
from app.services.parser.base_parser import BaseParser
from app.services.parser.pdf_parser import PDFExtractor
from app.services.parser.docx_parser import DocxExtractor
from app.services.parser.text_parser import TextExtractor
from app.services.parser.markdown_parser import MarkdownExtractor
from app.services.parser.html_parser import HTMLParser

class ParserFactory:
    _parsers = [
        PDFExtractor(),
        DocxExtractor(),
        TextExtractor(),
        MarkdownExtractor(),
        HTMLParser(),
    ]

    @classmethod
    def get_parser(cls, filepath: str) -> BaseParser:
        ext = os.path.splitext(filepath)[1].lower()
        for parser in cls._parsers:
            if ext in parser.get_file_extensions():
                return parser
        raise ValueError(f"Unsupported file type: {ext}")
