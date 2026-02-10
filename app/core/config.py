from app import logger
from dotenv import load_dotenv
import os
import json
from dataclasses import dataclass, field
from app.prompts.prompts import ToneStyle, get_system_prompt
from app.core.hardware import HardwareDetector

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
    top_n: int = 10


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
        top_k=20,
        top_n=10
    ),
    max_conversation_turns=10
)

class Config:
    LLM_PROVIDER = os.getenv("LLM_PROVIDER")
    LLM_API_KEY = os.getenv("LLM_API_KEY")
    WEB_SEARCH_API_KEY = os.getenv("WEB_SEARCH_API_KEY")
    CSE_ID = os.getenv("CSE_ID")
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
    COHERE_API_KEY = os.getenv("COHERE_API_KEY")
    OPENALEX_API_KEY = os.getenv("OPENALEX_API_KEY")
    DATA_DIR = os.getenv("DATA_DIR", "source_files/")
    INDEX_DIR = os.getenv("INDEX_DIR", "index_storage/")
    STORAGE_DIR = os.getenv("STORAGE_DIR", "conversations/") 
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
        TOP_N = admin.rag.top_n
        
        RERANKING_MODEL = os.getenv("RERANKING_MODEL", "BAAI/bge-reranker-v2-m3")
        EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")

        # Conversation settings
        MAX_CONVERSATION_TURNS = admin.max_conversation_turns
        HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", 30.0))  # seconds
        WEB_SEARCH_NUM_RESULTS = int(os.getenv("WEB_SEARCH_NUM_RESULTS", 5))
        COLLECTION_NAME = "chat_collection"
        EXEC_MAX_RETRIES = int(os.getenv("EXEC_MAX_RETRIES", 3))

        # Hardware Acceleration Settings
        USE_GPU_ACCELERATION, HARDWARE_MODE = HardwareDetector.should_use_acceleration()
        CPU_COUNT = os.cpu_count() or 4
        
        # Sandbox / Docker execution settings (user-configurable via env)
        SANDBOX_NANO_CPUS = int(os.getenv("SANDBOX_NANO_CPUS", "500000000"))  # 0.5 CPU
        SANDBOX_MEM_LIMIT = os.getenv("SANDBOX_MEM_LIMIT", "2g")
        SANDBOX_MEM_RESERVATION = os.getenv("SANDBOX_MEM_RESERVATION", "1g")
        SANDBOX_MEMSWAP_LIMIT = os.getenv("SANDBOX_MEMSWAP_LIMIT", "2g")
        SANDBOX_PIDS_LIMIT = int(os.getenv("SANDBOX_PIDS_LIMIT", "64"))
        SANDBOX_SHM_SIZE = os.getenv("SANDBOX_SHM_SIZE", "64m")
        SANDBOX_AUTO_REMOVE = os.getenv("SANDBOX_AUTO_REMOVE", "False").lower() in ("1", "true", "yes")

    except Exception as e:
        logger.error(f"Error in configuration: {e}")
        raise RuntimeError(f"Error in configuration: {e}") from e