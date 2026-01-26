from fastapi import APIRouter, Request, UploadFile, File
from fastapi.responses import JSONResponse
from app import logger
from app.services.rag_service.rag_execution_service import RAGExecutionService
import os

ingest_bp = APIRouter()

def init_ingest_routes(app, history_store):
    rag_service = RAGExecutionService()

    @ingest_bp.get('/api/ingest/files')
    async def list_ingest_files():
        """List all files in the global RAG corpus."""
        try:
            files = await history_store.list_rag_files()
            return JSONResponse(content={"files": files})
        except Exception as e:
            logger.error(f"Error listing RAG files: {e}")
            return JSONResponse(content={"error": str(e)}, status_code=500)

    @ingest_bp.post('/api/ingest/')
    async def ingest_files(request: Request):
        """Upload files to the global RAG corpus."""
        try:
            form = await request.form()
            # Support both `files` and `file` field names from different clients
            files = [val for key, val in form.multi_items() if key in ("files", "file") and getattr(val, 'filename', None)]
            
            if not files:
                return JSONResponse(content={"error": "No files provided"}, status_code=400)

            saved_paths = []
            for file in files:
                if file.filename:
                    path = await history_store.save_rag_file(file)
                    saved_paths.append(path)
            
            # Trigger RAG Re-indexing (Full Rebuild)
            logger.info(f"Triggering full RAG index rebuild for {len(saved_paths)} new files...")
            await rag_service.rebuild_index()
            
            return JSONResponse(content={
                "message": f"Successfully ingested {len(saved_paths)} files and updated index.",
                "files": saved_paths
            })
        except Exception as e:
            logger.error(f"Error during ingestion: {e}")
            return JSONResponse(content={"error": str(e)}, status_code=500)

    @ingest_bp.delete('/api/ingest/files/{filename}')
    async def delete_ingest_file(filename: str):
        """Delete a file from the global RAG corpus."""
        try:
            await history_store.delete_rag_file(filename)
            
            # Re-index to remove the document (Full Rebuild)
            logger.info(f"File {filename} deleted. Rebuilding index...")
            await rag_service.rebuild_index()
            
            return JSONResponse(content={"message": f"File {filename} deleted and index rebuilt."})
        except Exception as e:
            logger.error(f"Error deleting RAG file: {e}")
            return JSONResponse(content={"error": str(e)}, status_code=500)

    app.include_router(ingest_bp)
