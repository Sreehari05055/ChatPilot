import os
import sys
import logging
import argparse
from pathlib import Path

# Add the project root to sys.path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

from app.services.parser.html_parser import HTMLParser

def test_html_parsing(html_path: str, output_path: str = None):
    """
    Tests the Docling-based HTMLParser on a given file.
    """
    if not os.path.exists(html_path):
        logger.error(f"File not found: {html_path}")
        return

    logger.info(f"🚀 Starting HTML extraction for: {html_path}")
    
    try:
        extractor = HTMLParser()
        result = extractor.extract(html_path)
        
        if not result:
            logger.error("❌ Extraction returned None or empty.")
            return

        # Extract content and metadata from the result dictionary
        content = result.get("content", "")
        metadata = result.get("metadata", {})

        if not content:
            logger.error("❌ Extraction returned empty content string.")
            return

        logger.info(f"✅ Extraction successful! (Size: {len(content)} characters)")
        logger.info(f"📂 Metadata: {metadata}")
        
        # Display a snippet
        snippet_size = 5000
        logger.info("-" * 40)
        logger.info(f"Content Snippet (First {snippet_size} chars):")
        logger.info("-" * 40)
        print(content[:snippet_size] + ("..." if len(content) > snippet_size else ""))
        logger.info("-" * 40)

        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"💾 Full output saved to: {output_path}")

    except Exception as e:
        logger.exception(f"An error occurred during testing: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Docling HTML extraction.")
    parser.add_argument("html_path", help="Path to the HTML file to test")
    parser.add_argument("--output", "-o", help="Path to save the extracted markdown")
    
    args = parser.parse_args()
    
    test_html_parsing(args.html_path, args.output)
