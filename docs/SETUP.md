# ChatPilot Setup Guide

## Prerequisites

- Python 3.9 or higher
- pip (Python package manager)
- Docker (required for secure code execution sandbox)
- **LLM API Key** - One of the following is required:
  - OpenAI (GPT-4o)
  - Anthropic (Claude 3.5 Sonnet)
  - DeepSeek (DeepSeek-V3/R1)
  - Google (Gemini-1.5 Pro/Flash)
- **RAG Configuration** (Embedding & Reranking):
  - **Local (BAAI)**: Fast, offline, no API key needed
  - **Cloud (OpenAI / Cohere)**: High-performance embeddings and reranking
- Web Search API Key (Optional):
  - **Tavily API Key** (Optimized for research/agents)
  - **Google Custom Search** API key + CSE ID

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

ChatPilot supports multiple providers for both LLM and RAG features.

**Required (LLM Provider):**
Choose your primary LLM and get its API key:
- [OpenAI](https://platform.openai.com/)
- [Anthropic](https://console.anthropic.com/)
- [DeepSeek](https://platform.deepseek.com/)
- [Google AI](https://aistudio.google.com/)

**RAG Support (Embeddings & Reranking):**
You can mix and match any combination of providers:
- **Embeddings**: `openai`, `cohere`, or `local` (BAAI BGE)
- **Reranker**: `cohere` or `local` (BAAI BGE)

> [!NOTE]
> If you select `cohere` or `openai` as a provider but do NOT provide the corresponding API key, ChatPilot will automatically fall back to **local** models to ensure the app continues to function.

**Optional (Search):**
- **Tavily**: Recommended for web research.
- **OpenAlex**: For scholar research tools.

### 4. Set up environment variables

Create a `.env` file in the project root with the following structure:

```bash
# --- LLM CONFIGURATION ---
LLM_PROVIDER=openai  # openai, anthropic, deepseek, or google
MODEL_NAME=gpt-4o     # The specific model version to use
LLM_API_KEY=your_api_key_here

# --- RAG CONFIGURATION (MIX & MATCH) ---
# Choose your embedding and reranker providers independently
EMBEDDING_PROVIDER=openai  # Options: openai, cohere, local
RERANKER_PROVIDER=local    # Options: cohere, local

# --- SEARCH CONFIGURATION (OPTIONAL) ---
TAVILY_API_KEY=your_tavily_api_key
OPENALEX_API_KEY=your_openalex_api_key

# OR Google Custom Search
WEB_SEARCH_API_KEY=your_google_api_key
CSE_ID=your_cse_id
```

### 5. Build the Docker sandbox image

For secure code execution / data analysis:
```bash
docker build -t python-sandbox:latest -f Dockerfile .
```

### 6. Run ChatPilot

```bash
python main.py
```

## Advanced Configuration

### Resource Limits (Docker Sandbox)
Adjust container resource limits in `.env` to match your hardware:
- `SANDBOX_NANO_CPUS`: CPU limit (e.g., 500000000 is 0.5 CPU)
- `SANDBOX_MEM_LIMIT`: Memory limit (e.g., 2g)

### RAG Performance Tuning
Edit `app/core/config.py` to adjust:
- `chunk_size`: Size of document segments (default 512)
- `top_k`: Number of chunks picked by initial search (default 20)
- `top_n`: Number of chunks kept after reranking (default 10)


## Usage

### Document Ingestion
Upload files via the UI (PDF, TXT, DOCX, MD). ChatPilot supports OCR automatically. Documents are indexed instantly and available for the RAG pipeline.

### Web & Scholar Research
- **WebResearch**: Uses Tavily/Google to synthesize answers from the web.
- **Scholar Research**: Uses OpenAlex for multi-step academic research.
