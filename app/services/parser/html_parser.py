from lxml import etree, html
from sklearn import tree
from app.services.parser.base_parser import BaseParser
from app import logger


class HTMLParser(BaseParser):
    """
    Extracts text content from HTML files.
    Usage:
        content = HTMLParser().extract(filepath)
    """
    def get_file_extensions(self):
        return ['.html']
    
    def extract(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                tree = html.fromstring(f.read())

            chunks = []

            # Iterate over headings to create logical chunks
            for heading in tree.xpath('//h1|//h2|//h3'):
                title = heading.text_content().strip()
                content = []

                # Include siblings until the next heading
                for sibling in heading.itersiblings():
                    if sibling.tag in ['h1', 'h2', 'h3']:
                        break
                    if sibling.tag == 'p':
                        content.append(sibling.text_content().strip())
                    elif sibling.tag == 'ul':
                        for li in sibling.xpath('.//li'):
                            content.append("- " + li.text_content().strip())
                    elif sibling.tag == 'ol':
                        for idx, li in enumerate(sibling.xpath('.//li'), start=1):
                            content.append(f"{idx}. {li.text_content().strip()}")
                    elif sibling.tag == 'table':
                        for row in sibling.xpath('.//tr'):
                            cells = [c.text_content().strip() for c in row.xpath('.//th|.//td')]
                            content.append(" | ".join(cells))

                chunk_text = title + "\n" + "\n".join(content)
                cleaned_chunk = self.clean_for_embeddings(chunk_text)
                chunks.append(cleaned_chunk)

            return chunks
        except Exception as e:
            logger.exception(f"HTML extraction failed for %s: %s", filepath, e)
            return []