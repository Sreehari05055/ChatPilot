import pymupdf4llm
import pymupdf.layout
from app.services.parser.base_parser import BaseParser
from app import logger

class PDFExtractor(BaseParser):
    """
    Extracts text content from PDF files.
    Usage:
        content = PDFExtractor().extract(filepath)
    """
    def get_file_extensions(self):
        return ['.pdf']
    
    def extract(self, filepath):
        try:
            # Disable table detection to avoid the bug
            md_text = pymupdf4llm.to_markdown(
                filepath,
                write_images=False,
                table_strategy="none"  # ← Disable table detection
            )
            
            if not md_text or not md_text.strip():
                logger.warning(f"PDF {filepath} extracted empty content")
                return ""
            
            cleaned_md_text = self.clean_markdown(md_text)
            cleaned_text_for_embeddings = self.clean_for_embeddings(cleaned_md_text)
            return cleaned_text_for_embeddings
            
        except Exception as e:
            logger.error(f"Error extracting PDF {filepath}: {e}", exc_info=True)
        # Fallback to basic PyMuPDF extraction (always works)
        try:
            logger.info(f"Using fallback: basic PyMuPDF extraction...")
            doc = pymupdf.open(filepath)
            
            if len(doc) == 0:
                logger.warning(f"PDF has no pages: {filepath}")
                doc.close()
                return ""
            
            logger.info(f"PDF has {len(doc)} pages")
            
            # Extract text from all pages
            all_text = []
            for page_num in range(len(doc)):
                try:
                    page = doc[page_num]
                    text = page.get_text("text")  # Simple text extraction
                    
                    if text.strip():
                        # Add page marker for better context
                        all_text.append(f"[Page {page_num + 1}]\n{text}")
                    else:
                        logger.debug(f"Page {page_num + 1} has no text")
                        
                except Exception as e:
                    logger.warning(f"Error extracting page {page_num + 1}: {e}")
                    continue
            
            doc.close()
            
            if not all_text:
                logger.warning(f"No extractable text found in any page of: {filepath}")
                return ""
            
            combined_text = "\n\n".join(all_text)
            logger.info(f"✅ Fallback extraction succeeded: {len(combined_text)} chars from {len(all_text)} pages")
            
            # Clean the text
            cleaned_text = self.clean_for_embeddings(combined_text)
            
            if not cleaned_text.strip():
                logger.warning(f"Cleaning resulted in empty text for: {filepath}")
                return ""
            
            logger.info(f"Final cleaned text: {len(cleaned_text)} chars")
            return cleaned_text
            
        except Exception as e:
            logger.error(f"❌ Fallback extraction also failed for {filepath}: {type(e).__name__}: {e}", exc_info=True)
            return ""