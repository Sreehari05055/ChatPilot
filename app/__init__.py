import tracemalloc
import os
import logging
from contextlib import asynccontextmanager
from slowapi.util import get_remote_address
import httpx
from slowapi import Limiter

# Ensure `configuration/admin_config.json` exists at startup with sensible defaults
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(PROJECT_ROOT, "configuration")

tracemalloc.start()
limiter = Limiter(key_func=get_remote_address)
log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app_errors.log')

logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename=log_file,
    filemode="a"
)

logger = logging.getLogger("ChatLogger")
logger.setLevel(logging.DEBUG)

from fastapi import FastAPI
from app.core.config import Config
from slowapi.middleware import SlowAPIMiddleware
from app.services.rag_service import RAGExecutionService
from app.services.web.web_search_factory import WebSearchProviderFactory
from app.services.state_manager import FileHistoryStore
from starlette.middleware.sessions import SessionMiddleware
from app.services.code_execution.execution_service import CodeExecutionService
from app.services.langchain_handler.tool_executor import ToolExecutor
from fastapi.middleware.cors import CORSMiddleware

# Ensure application data directories exist (after Config import)
if not os.path.exists(Config.DATA_DIR):
    os.makedirs(Config.DATA_DIR, exist_ok=True)
if not os.path.exists(Config.INDEX_DIR):
    os.makedirs(Config.INDEX_DIR, exist_ok=True)

def create_app() -> FastAPI:

    history_store = FileHistoryStore(storage_dir="conversations", rag_dir=Config.DATA_DIR)

    if not Config.LLM_API_KEY:  
        logger.error("LLM_API_KEY environment variable is not set")
    if not Config.COHERE_API_KEY:
        logger.error("COHERE_API_KEY environment variable is not set")  

    http_client = httpx.AsyncClient()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            await RAGExecutionService().init_index()
            yield
        finally:
            await http_client.aclose()

    app = FastAPI(lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5000", "http://localhost:3000", "http://localhost:5173"],  # For production robustness, though you might want to restrict this in the future
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(
            SessionMiddleware, 
            secret_key="secret-key" # Change this to a real secret
        )
    
    app.add_middleware(SlowAPIMiddleware)

    from app.routes.chatbot_routes import init_chatbot_routes
    from app.routes.ingest_routes import init_ingest_routes
    init_ingest_routes(app, history_store)
    init_chatbot_routes(app, Config.system_prompt, history_store, http_client)


    return app


__all__ = ["create_app", "logger", "limiter", "tracemalloc"]
