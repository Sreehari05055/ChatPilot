import tracemalloc
import os
import logging
from contextlib import asynccontextmanager
from slowapi.util import get_remote_address
import openai
import httpx
import asyncio
from slowapi import Limiter
import json

# Ensure `configuration/admin_config.json` exists at startup with sensible defaults
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(PROJECT_ROOT, "configuration")
ADMIN_CONFIG_PATH = os.path.join(CONFIG_DIR, "admin_config.json")
DEFAULT_ADMIN_CONFIG = {
    "model": {"temperature": 0.4, "max_tokens": 1000, "top_p": 1.0},
    "rag": {"chunk_size": 500, "chunk_overlap": 50, "top_k": 2},
    "max_conversation_turns": 10,
}

try:
    if not os.path.exists(ADMIN_CONFIG_PATH):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(ADMIN_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_ADMIN_CONFIG, f, indent=2, ensure_ascii=False)
except Exception:
    # If creation fails, continue; Config import will handle errors
    pass

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
from app.services.chatbot_service import ChatbotService
from app.services.rag_service import RAGPipeline
from app.services.web.web_search_factory import WebSearchProviderFactory
from app.services.llm_engine.factory import create_llm_engine
from app.services.llm_engine.client_factory import build_llm_client
from app.prompts.system_prompt import system_prompt
from app.services.state_manager import InMemoryStore
from starlette.middleware.sessions import SessionMiddleware
import itsdangerous
from app.services.code_execution.execution_service import CodeExecutionService
from app.services.web.web_fetch import WebFetchService

# Ensure application data directories exist (after Config import)
if not os.path.exists(Config.DATA_DIR):
    os.makedirs(Config.DATA_DIR, exist_ok=True)
if not os.path.exists(Config.UPLOAD_DIR):
    os.makedirs(Config.UPLOAD_DIR, exist_ok=True)
if not os.path.exists(Config.INDEX_DIR):
    os.makedirs(Config.INDEX_DIR, exist_ok=True)


def create_app() -> FastAPI:

    history_store = InMemoryStore()

    if not Config.LLM_API_KEY:
        logger.error("LLM_API_KEY environment variable is not set")

    # Shared clients
    http_client = httpx.AsyncClient()
    web_search_service = WebSearchProviderFactory.get_provider(Config, http_client)
    web_fetch_service = WebFetchService()
    # Build provider-specific LLM client and engine, then inject into services
    provider = getattr(Config, "LLM_PROVIDER", None)
    if not provider:
        logger.error("LLM_PROVIDER is not configured in Config; please set it explicitly.")
        raise RuntimeError("LLM_PROVIDER is not configured; no default provider allowed.")
    
    llm_client = build_llm_client(provider, Config)
    llm_engine = create_llm_engine(provider, llm_client)
    code_executor = CodeExecutionService(llm_engine)
    rag_service = RAGPipeline()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Initialize RAG index after trees are saved
        try:
            rag_service.init_index()
            yield
        finally:
            await http_client.aclose()

    app = FastAPI(lifespan=lifespan)
    app.add_middleware(
            SessionMiddleware, 
            secret_key="secret-key" # Change this to a real secret
        )
    
    app.add_middleware(SlowAPIMiddleware)

    from app.routes.chatbot_routes import init_chatbot_routes
    init_chatbot_routes(app, llm_engine, web_search_service, web_fetch_service, rag_service, system_prompt, history_store, code_executor )

    return app


__all__ = ["create_app", "logger", "limiter", "tracemalloc"]
