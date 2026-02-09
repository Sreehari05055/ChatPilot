#!/usr/bin/env python3
"""
Simple test script to run OpenAlex `semantic_scholar_search`.
Usage: python scripts/test_openalex_search.py "query" --count 10
"""
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import asyncio
import logging
from pathlib import Path
from app.services.scholar_research.openalex_service import OpenAlexResearchService
from app.core.config import Config

project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)
    

# scripts/test_openalex_search.py
async def main():
    query = "machine learning applications in drug discovery" # Use a descriptive sentence
    svc = OpenAlexResearchService()
    
    try:
        # Pass parameters explicitly to test the filter logic
        results = await svc.semantic_scholar_search(
            query=query, 

        )
        
        print(f"OpenAlex Search Results for query: '{query}': {results}")
                
    except Exception as e:
        print(f"Execution Error: {e}")
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
