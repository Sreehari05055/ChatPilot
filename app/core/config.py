from dotenv import load_dotenv
import os
import json

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
ENV_PATH = os.path.join(PROJECT_ROOT, ".env")
ADMIN_CONFIG_FILE = os.path.join(os.path.dirname(BASE_DIR), "configuration", "admin_config.json")


load_dotenv(dotenv_path=ENV_PATH)

class Config:
    LLM_PROVIDER = os.getenv("LLM_PROVIDER")
    WEB_SEARCH_ENABLED = os.getenv("WEB_SEARCH_ENABLED")
    LLM_API_KEY = os.getenv("LLM_API_KEY")
    WEB_SEARCH_API_KEY = os.getenv("WEB_SEARCH_API_KEY")
    CSE_ID = os.getenv("CSE_ID")

    # WEB_SEARCH_ENABLED: environment overrides admin_config.json
    env_web_search = os.getenv("WEB_SEARCH_ENABLED")

    DB_TYPE = "file"  # v1: Always use file

    # Static app settings with env overrides
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads/")
    DATA_DIR = os.getenv("DATA_DIR", "source_files/")
    INDEX_DIR = os.getenv("INDEX_DIR", "index_storage/")
    # Load admin_config.json for other settings
    try:
        with open(ADMIN_CONFIG_FILE, "r", encoding="utf-8") as f:
            admin_config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        raise RuntimeError(f"Invalid or missing admin_config.json: {e}")

    try:
        MODEL_NAME = os.getenv("MODEL_NAME")
        TEMPERATURE = admin_config["model"]["temperature"]
        MAX_TOKENS = admin_config["model"]["max_tokens"]
        TOP_P = admin_config["model"]["top_p"]
        STREAM = True

        HTTP_TIMEOUT = 10
        WEB_SEARCH_NUM_RESULTS = 5
        CHUNK_SIZE = admin_config["rag"]["chunk_size"]
        CHUNK_OVERLAP = admin_config["rag"]["chunk_overlap"]
        TOP_K = admin_config["rag"]["top_k"]

        MAX_CONVERSATION_TURNS = admin_config["max_conversation_turns"]
        
        EMBEDDING_DIM = 1024  # Dimension for BGE-2.0 models
        EMBEDDING_MODEL_NAME = "BAAI/bge-large-en-v1.5"
        COLLECTION_NAME = "chat_collection"
        MAX_RETRIES = 3
    except Exception as e:
        raise RuntimeError(f"admin_config.json is missing required fields or has invalid structure: {e}")
