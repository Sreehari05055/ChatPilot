from app import logger
from dotenv import load_dotenv
import os
import json
from dataclasses import dataclass, field
from app.prompts.prompts import ToneStyle, get_system_prompt

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
ENV_PATH = os.path.join(PROJECT_ROOT, ".env")

load_dotenv(dotenv_path=ENV_PATH)

@dataclass
class ModelConfig:
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 0.9


@dataclass
class RAGConfig:
    chunk_size: int = 512
    chunk_overlap: int = 50
    top_k: int = 5


@dataclass
class AdminConfig:
    """User-configurable settings - modify values here directly"""
    model: ModelConfig = field(default_factory=ModelConfig)
    rag: RAGConfig = field(default_factory=RAGConfig)
    max_conversation_turns: int = 10


# ============================================
# EDIT YOUR SETTINGS HERE
# ============================================
admin = AdminConfig(
    model=ModelConfig(
        temperature=0.7,
        max_tokens=4096,
        top_p=0.9
    ),
    rag=RAGConfig(
        chunk_size=512,
        chunk_overlap=50,
        top_k=20
    ),
    max_conversation_turns=10
)

class Config:
    LLM_PROVIDER = os.getenv("LLM_PROVIDER")
    WEB_SEARCH_ENABLED = os.getenv("WEB_SEARCH_ENABLED")
    LLM_API_KEY = os.getenv("LLM_API_KEY")
    WEB_SEARCH_API_KEY = os.getenv("WEB_SEARCH_API_KEY")
    CSE_ID = os.getenv("CSE_ID")
    env_web_search = os.getenv("WEB_SEARCH_ENABLED")
    DATA_DIR = os.getenv("DATA_DIR", "source_files/")
    INDEX_DIR = os.getenv("INDEX_DIR", "index_storage/")

    try:
        system_prompt = get_system_prompt(ToneStyle.PROFESSIONAL)
        MODEL_NAME = os.getenv("MODEL_NAME")

        # Model settings (from AdminConfig)
        TEMPERATURE = admin.model.temperature
        MAX_TOKENS = admin.model.max_tokens
        TOP_P = admin.model.top_p
        STREAM = True

        # RAG settings (from AdminConfig)
        CHUNK_SIZE = admin.rag.chunk_size
        CHUNK_OVERLAP = admin.rag.chunk_overlap
        TOP_K = admin.rag.top_k

        # Conversation settings
        MAX_CONVERSATION_TURNS = admin.max_conversation_turns
        
        HTTP_TIMEOUT = 30  # seconds
        WEB_SEARCH_NUM_RESULTS = 5
        EMBEDDING_DIM = 1024  # Dimension for BGE-2.0 models
        EMBEDDING_MODEL_NAME = "BAAI/bge-large-en-v1.5"
        COLLECTION_NAME = "chat_collection"
        EXEC_MAX_RETRIES = 3

    except Exception as e:
        logger.error(f"Error in configuration: {e}")
        raise RuntimeError(f"Error in configuration: {e}") from e