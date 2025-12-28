import httpx
import os
import tempfile

from app.services.parser.html_parser import HTMLParser
from app.services.parser.pdf_parser import PDFExtractor
from app import logger

class WebFetchService:
    
    def _parse_html(self, html: str) -> str:
        """Parse HTML directly (no file needed)."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.html', encoding='utf-8') as tmp:
            tmp.write(html)
            tmp_path = tmp.name
        
        try:
            return HTMLParser().extract(tmp_path)
        finally:
            os.unlink(tmp_path)
    
    async def _parse_pdf(self, content: bytes, url: str) -> str:
        """Save PDF temp, parse, delete."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            text = PDFExtractor().extract(tmp_path)
            return text
        finally:
            os.unlink(tmp_path)

    async def fetch_and_parse(self, url: str) -> str:
        """Fetch URL, detect type, parse content."""
        
        # 1. Fetch
        async with httpx.AsyncClient() as client:
            response = await client.get(url, follow_redirects=True, timeout=30)
            content_type = response.headers.get('content-type', '')
        # 2. Route based on type
        if 'html' in content_type:
            return self._parse_html(response.text)
        
        
        elif 'pdf' in content_type:
            parsed_pdf = await self._parse_pdf(response.content, url)
            return parsed_pdf
        
        else:
            # Default: treat as text
            return response.text