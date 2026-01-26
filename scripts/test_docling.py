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

from app.services.parser.pdf_parser import PDFExtractor

def test_pdf_parsing(pdf_path: str, output_path: str = None):
    """
    Tests the Docling-based PDFExtractor on a given file.
    """
    if not os.path.exists(pdf_path):
        logger.error(f"File not found: {pdf_path}")
        return

    logger.info(f"🚀 Starting extraction for: {pdf_path}")
    
    try:
        extractor = PDFExtractor()
        result = extractor.extract(pdf_path)
        
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

        # Check for table-like structure (markdown pipes)
        if "|" in content and "---|" in content:
            logger.info("📊 Detection: Tables found in the output!")
        else:
            logger.info("ℹ️ No tables detected in the first 1000 characters.")

        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"💾 Full output saved to: {output_path}")

    except ImportError as e:
        logger.error(f"Failed to import docling. Did you run 'pip install docling'? Error: {e}")
    except Exception as e:
        logger.exception(f"An error occurred during testing: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Docling PDF extraction.")
    parser.add_argument("pdf_path", help="Path to the PDF file to test")
    parser.add_argument("--output", "-o", help="Path to save the extracted markdown")
    
    args = parser.parse_args()
    test_pdf_parsing(args.pdf_path, args.output)
