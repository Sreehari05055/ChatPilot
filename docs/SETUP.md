# ChatPilot Setup Guide

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Docker (required for secure code execution sandbox)
- LLM API key - OpenAI or Anthropic (required)
- **RAG Provider** (choose one):
  - **Local**: No API key needed - uses HuggingFace embeddings (BAAI BGE-small-en-v1.5) + BGE reranker (fully offline)
  - **Cloud**: Cohere API key (1024D embeddings with built-in reranking)
- Web Search API key (optional):
  - **Tavily API key** (recommended for accuracy), OR
  - Google Cloud Custom Search API key + CSE ID

## Installation

### 1. Clone the repository
```bash
git clone https://github.com/Sreehari05055/ChatPilot.git
cd chatpilot
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Get API Keys

**Required:**
1.  **LLM Provider** - Get an API key from:
    - [OpenAI](https://platform.openai.com/api-keys) (recommended: GPT-4o)
    - OR [Anthropic](https://console.anthropic.com/) (Claude models)
2.  **RAG Provider** (choose one):
    - **Local**: No setup needed - automatically uses HuggingFace models (BAAI BGE-small-en-v1.5 embeddings + BGE reranker-v2-m3)
    - **Cloud**: Sign up at [cohere.com](https://cohere.com/) for 1024D embeddings with built-in reranking

**Optional (for web search):**
- **Tavily** (recommended): Get your key at [tavily.com](https://tavily.com)
- OR **Google Custom Search**: 
  - API key from [Google Cloud Console](https://console.cloud.google.com/)
  - CSE ID from [cse.google.com](https://cse.google.com)

### 4. Set up environment variables

Create a `.env` file in the project root with your API keys:

```bash
# Required - Choose your LLM provider
LLM_PROVIDER=openai  # or "anthropic"
LLM_API_KEY=your_openai_or_anthropic_key

# RAG Provider (optional - defaults to local HuggingFace if not set)
# Leave COHERE_API_KEY empty to use local BGE embeddings
COHERE_API_KEY=  # Add your key here only if you want to use Cohere embeddings

# Optional - Web Search (choose one)
TAVILY_API_KEY=your_tavily_api_key  # Recommended for accuracy

# OR use Google Custom Search instead
WEB_SEARCH_API_KEY=your_google_api_key
CSE_ID=your_custom_search_engine_id

# Optional - Model selection
MODEL_NAME=gpt-4o  # or gpt-4o-mini, claude-3-5-sonnet-20241022, etc.
```

### 5. Build the Docker sandbox image

For secure code execution, build the sandbox container:
```bash
docker build -t python-sandbox:latest -f Dockerfile .
```

### 6. Run ChatPilot

```bash
python main.py
```

## Configuration Options

### Customizing Model & RAG Settings

Edit `app/core/config.py` to adjust:

**Model Configuration:**
```python
admin = AdminConfig(
    model=ModelConfig(
        temperature=0.7,      # 0.0-2.0: controls randomness
        max_tokens=4096,      # Maximum response length
        top_p=0.9            # 0.0-1.0: nucleus sampling
    ),
    rag=RAGConfig(
        chunk_size=512,      # How documents are split
        chunk_overlap=50,    # Overlap between chunks
        top_k=20            # Number of chunks to retrieve
    ),
    max_conversation_turns=10  # Chat history context
)
```

**System Prompt Customization:**
```python
# In config.py, change the tone style:
system_prompt = get_system_prompt(ToneStyle.PROFESSIONAL)
# Options: PROFESSIONAL, FRIENDLY, CONCISE, CREATIVE
```

### Web Search Providers

ChatPilot supports two web search providers:

1.  **Tavily** (Recommended): More accurate, optimized for AI applications
    - Get your API key at [tavily.com](https://tavily.com)
    - Set `TAVILY_API_KEY` in `.env`
2.  **Google Custom Search**: Traditional search with broader coverage
    - Get API key from Google Cloud Console
    - Create a Custom Search Engine at [cse.google.com](https://cse.google.com)
    - Set `WEB_SEARCH_API_KEY` and `CSE_ID` in `.env`


## Usage

### Starting the server
```bash
python main.py
```

Server runs on `http://localhost:8000` with 4 worker processes for production-grade performance.

### Adding documents for RAG

Use the web interface to upload documents:
1.  Navigate to the ingestion section in the UI
2.  Upload your files (PDF, TXT, HTML, DOCX, MD, Scanned documents (OCR-enabled))  
3.  Documents are automatically indexed and ready for Q&A

No need to manually place files in directories or restart the server.

### Updating configuration

**To change API keys or add new providers:**
- Edit the `.env` file in the project root
- Restart the server to apply changes

**To adjust model behavior, RAG settings, or system prompt:**
- Edit `app/core/config.py`
- Restart the server to apply changes