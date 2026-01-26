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

from app.services.parser.image_parser import ImageExtractor

def test_image_parsing(image_path: str, output_path: str = None):
    """
    Tests the Docling-based ImageExtractor on a given file.
    """
    if not os.path.exists(image_path):
        logger.error(f"File not found: {image_path}")
        return

    logger.info(f"🚀 Starting OCR extraction for: {image_path}")
    
    try:
        extractor = ImageExtractor()
        result = extractor.extract(image_path)
        
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
    parser = argparse.ArgumentParser(description="Test Docling Image OCR extraction.")
    parser.add_argument("image_path", help="Path to the image file to test")
    parser.add_argument("--output", "-o", help="Path to save the extracted markdown")
    
    args = parser.parse_args()
    
    # Ensure environment variables for Windows symlinks are mentioned or set
    if os.name == 'nt':
        os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"
        
    test_image_parsing(args.image_path, args.output)
