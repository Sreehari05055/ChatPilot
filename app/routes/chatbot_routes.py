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


def init_chatbot_routes(app, llm_engine, web_search_service, web_fetch_service, rag_service, system_prompt, history_store, code_executor):

    @chatbot_bp.post('/api/chat', response_class=StreamingResponse)
    @limiter.limit("10/minute")
    async def get_bot_response(request: Request):
        session_upload_dir = None  # For cleanup tracking
        try:
            
            session_id = (
                request.headers.get('X-Session-ID') or
                request.session.get("user_id") or
                request.query_params.get('session_id') or
                str(uuid.uuid4())
            )
        
            logger.info(f"Using session: {session_id}")
            request.session["user_id"] = session_id
        
                    
            uploaded_files = []
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
                
                # Save files to uploads/session_id/
                if files:
                    session_upload_dir = os.path.join(Config.UPLOAD_DIR, session_id)
                    os.makedirs(session_upload_dir, exist_ok=True)
                    
                    for file in files:
                        filepath = os.path.join(session_upload_dir, file.filename)
                        content = await file.read()
                        with open(filepath, 'wb') as f:
                            f.write(content)
                        uploaded_files.append(filepath)
                        logger.info(f"Saved: {filepath}")
            else:
                body = await request.json()
                question = body.get('question')

                if body.get('session_id'):
                    session_id = body.get('session_id')
                    request.session["user_id"] = session_id
            
            if not question:
                raise ValueError("Question field is required.")
            
            chatbot_service = ChatbotService(llm_engine, web_search_service, web_fetch_service, rag_service, system_prompt, store=history_store, session_id=session_id, code_executor=code_executor)

            async def event_stream():
                try:
                    async for chunk in chatbot_service._generate_response(question, uploaded_files=uploaded_files):
                        yield chunk
                finally:
                    
                    if session_upload_dir and os.path.exists(session_upload_dir):
                        shutil.rmtree(session_upload_dir)
                        logger.info(f"Cleaned: {session_upload_dir}")

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
            if session_upload_dir and os.path.exists(session_upload_dir):
                shutil.rmtree(session_upload_dir)
            logger.exception("Unexpected error:")
            return JSONResponse(content={"error": "An unexpected error occurred. Please try again later."},
                                status_code=500)

    app.include_router(chatbot_bp)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
