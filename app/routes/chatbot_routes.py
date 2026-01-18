# app/routes/chatbot_routes.py
import os
import shutil
from fastapi import Request
from fastapi.routing import APIRouter
from starlette.responses import JSONResponse, PlainTextResponse, StreamingResponse
from slowapi.errors import RateLimitExceeded
from starlette.status import HTTP_429_TOO_MANY_REQUESTS
from app import limiter, logger
from app.core.config import Config
from pydantic import ValidationError
from app.schemas.schemas import ChatRequest
import asyncio
import uuid
from app.services.chatbot_service import ChatbotService

chatbot_bp = APIRouter()


def _rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return PlainTextResponse("Rate limit exceeded", status_code=HTTP_429_TOO_MANY_REQUESTS)


def init_chatbot_routes(app, system_prompt, history_store, tool_executor, code_executor):

    @chatbot_bp.post('/api/chat', response_class=StreamingResponse)
    @limiter.limit("10/minute")
    async def get_bot_response(request: Request):
        try:
            
            session_id = (
                request.headers.get('X-Session-ID') or
                request.session.get("user_id") or
                request.query_params.get('session_id') or
                str(uuid.uuid4())
            )
        
            logger.info(f"Using session: {session_id}")
            request.session["user_id"] = session_id

            content_type = request.headers.get('content-type', '')
            if content_type.startswith('multipart/form-data'):
                form = await request.form()
                question = form.get('question')

                # Collect files
                files = [val for key, val in form.multi_items() if key == 'file' and val.filename]
                
                # Validate
                if len(files) > 3:
                    return JSONResponse(content={"error": "Maximum 3 files allowed"}, status_code=400)
                
                allowed_extensions = {'.csv', '.xlsx', '.xls'}
                for file in files:
                    ext = os.path.splitext(file.filename)[1].lower()
                    if ext not in allowed_extensions:
                        return JSONResponse(
                            content={"error": f"File type {ext} not supported. Use CSV or Excel."},
                            status_code=400
                        )
                
                # Save files to session's upload directory
                if files:
                    saved_paths = await history_store.save_uploaded_files(session_id, files)
                    file_metadata = await code_executor.analyze_files(saved_paths)
                    await history_store.save_session_metadata(session_id, file_paths=saved_paths, file_metadata=file_metadata)
            else:
                body = await request.json()
                question = body.get('question')
            
            if not question:
                raise ValueError("Question field is required.")
            
            # Instantiating ChatbotService with new signature
            chatbot_service = ChatbotService(
                system_prompt=system_prompt, 
                store=history_store, 
                session_id=session_id, 
                tool_executor=tool_executor
            )

            async def event_stream():
                # Files persist for multi-turn conversations
                async for chunk in chatbot_service._generate_response(question):
                    yield chunk

            return StreamingResponse(event_stream(), media_type='text/event-stream', headers={
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'X-Session-ID': session_id,
                })

        except RuntimeError as re:
            logger.error(f"RuntimeError: {re}")
            return JSONResponse(content={"error": str(re)}, status_code=500)
        except ValidationError as ve:
            return JSONResponse(content={"error": ve.errors()}, status_code=400)
        except KeyError as ke:
            logger.error(f"KeyError: {ke}")
            return JSONResponse(content={"error": f"Missing key in request: {str(ke)}"}, status_code=400)
        except ValueError as ve:
            logger.error(f"ValueError: {ve}")
            return JSONResponse(content={"error": f"Invalid data: {str(ve)}"}, status_code=400)
        except Exception as e:
            logger.exception("Unexpected error:")
            return JSONResponse(content={"error": "An unexpected error occurred. Please try again later."},
                                status_code=500)
    
    @chatbot_bp.get('/api/conversations')
    async def list_conversations(request: Request):
        """Get all conversation sessions for the user"""
        try:
            sessions = await history_store.list_sessions()
            return JSONResponse(content={"conversations": sessions})
        except Exception as e:
            logger.error(f"Error listing conversations: {e}")
            return JSONResponse(
                content={"error": "Failed to list conversations"},
                status_code=500
            )
    @chatbot_bp.get('/api/conversations/{session_id}')
    async def load_conversation(request: Request, session_id: str):
        """Get conversation messages for a specific session"""
        try:
            messages = await history_store.get_messages(session_id)
            metadata = await history_store.get_session_metadata(session_id)
            return JSONResponse(content={"session_id": session_id, "messages": messages, "metadata": metadata})
        except Exception as e:
            logger.error(f"Error loading conversation {session_id}: {e}")
            return JSONResponse(
                content={"error": f"Failed to load conversation {session_id}"},
                status_code=500
            )
    
    @chatbot_bp.delete('/api/conversations/{session_id}')
    async def delete_conversation(session_id: str, request: Request):
        """Delete conversation history and uploaded files"""
        try:
            # Clear entire session (messages + uploads in one directory)
            await history_store.clear_session(session_id)
            
            return JSONResponse(content={
                "message": "Conversation deleted successfully",
                "session_id": session_id
            })
        except Exception as e:
            logger.error(f"Error deleting conversation {session_id}: {e}")
            return JSONResponse(
                content={"error": "Failed to delete conversation"},
                status_code=500
            )
        
    @chatbot_bp.post('/api/conversations/new')
    async def new_conversation(request: Request):
        """Create a new conversation session"""
        session_id = str(uuid.uuid4())
        return JSONResponse(content={
            "session_id": session_id,
            "message": "New conversation created"
        })
    
    app.include_router(chatbot_bp)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
