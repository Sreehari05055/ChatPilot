#!/usr/bin/env python3
"""Simple script to trigger a full RAG index rebuild and verify success.

Run from the repo root:

    python scripts/test_build_index.py

Exits with code 0 on success, 1 on failure.
"""
import asyncio
import logging
import sys
import os
from pathlib import Path

project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)
    
from app.services.rag_service.rag_execution_service import RAGExecutionService
from app.services.rag_service.base_rag_pipeline import BaseRAGPipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    service = RAGExecutionService()

    logger.info("Starting full RAG index rebuild...")
    try:
        await service.rebuild_index()
    except Exception as e:
        logger.exception("Rebuild raised an exception")
        print("INDEX_BUILD_FAILED")
        sys.exit(1)

    if BaseRAGPipeline.index is None:
        logger.error("BaseRAGPipeline.index is None after rebuild")
        print("INDEX_BUILD_FAILED")
        sys.exit(1)

    logger.info("RAG index rebuild completed successfully")
    print("INDEX_BUILD_SUCCESS")
    # Optional: print index type for debug
    print(f"Index type: {type(BaseRAGPipeline.index)}")
    sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
