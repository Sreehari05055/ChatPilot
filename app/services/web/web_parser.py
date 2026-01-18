import os
import tempfile
from app.services.parser.html_parser import HTMLParser
from app.services.parser.pdf_parser import PDFExtractor
from app import logger

class WebContentParser:
    """Separated parsing logic from fetching logic."""
    
    @staticmethod
    def parse_html(html_content: str) -> str:
        """Parse HTML string into clean text."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.html', encoding='utf-8') as tmp:
            tmp.write(html_content)
            tmp_path = tmp.name
        
        try:
            # HTMLParser returns a list of chunks, we join them for the tool result
            chunks = HTMLParser().extract(tmp_path)
            return "\n\n".join(chunks) if isinstance(chunks, list) else str(chunks)
        except Exception as e:
            logger.error(f"HTML parsing failed: {e}")
            return html_content # Fallback to raw
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    @staticmethod
    def parse_pdf(pdf_bytes: bytes) -> str:
        """Parse PDF bytes into clean text."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name
        
        try:
            text = PDFExtractor().extract(tmp_path)
            return text
        except Exception as e:
            logger.error(f"PDF parsing failed: {e}")
            return "Error parsing PDF content."
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    @classmethod
    def parse_content(cls, content: any, content_type: str) -> str:
        """Route to appropriate parser based on content type."""
        if 'html' in content_type:
            return cls.parse_html(content if isinstance(content, str) else content.decode('utf-8', errors='ignore'))
        elif 'pdf' in content_type:
            return cls.parse_pdf(content if isinstance(content, bytes) else content.encode('utf-8'))
        else:
            return str(content)
