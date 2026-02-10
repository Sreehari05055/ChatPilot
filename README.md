# ChatPilot: Intelligent Agentic RAG & Autonomous Research Engine

**Demo video**: [Watch demo video](https://github.com/user-attachments/assets/12bcfb73-c5fa-46f7-8f48-2d235b98d3c8)

ChatPilot is a tool-augmented **Agentic Copilot** that goes beyond simple chat. It utilizes a single AI agent to interact with your local files, conduct deep web research, and perform autonomous data analysis through Python code execution.

**Demo Frontend:** [ChatPilot Frontend](https://github.com/Sreehari05055/Demo-frontend)

---

## Key Capabilities

### Agentic Context Reasoning & Document Intelligence
Powered by **Docling**, ChatPilot supports complex document understanding, including both scanned and digital formats. It utilizes a sophisticated **Agentic Intelligence** workflow:
- **Multi-Keyword Search**: The agent identifies and searches for multiple keywords to ensure comprehensive retrieval.
- **Context Re-evaluation**: Linked content and retrieved snippets are dynamically re-evaluated by the agent for relevance.
- **Sub-clause Retrieval**: The LLM can explicitly call for sub-clauses to retrieve deep context when simpler retrieval isn't enough.
- **Scanned Document Support**: Handles OCR and layout analysis for scanned PDFs and images using **Docling**.
- **PDF Highlighting**: Precise coordinate-based highlighting in the frontend - retrieved chunks are highlighted directly in the PDF viewer with element-level bounding boxes.

### Autonomous Data Analysis
Upload CSV or Excel files and ask for insights. ChatPilot functions as a **Data Analyst Agent**:
- **Planning**: Formulates a step-by-step analysis strategy.
- **Execution**: Writes and runs Python code in a secure sandbox.
- **Self-Correction**: If the code fails, the agent analyzes the error and automatically retries until it gets the result.

### Agentic Web Research
Integration with **Tavily** or **Google Custom Search** enables high-fidelity information gathering:
- **Deep Research**: Conducts multi-step, agentic research loops to generate thorough and structured reports—ideal for deep **competitor analysis** and market trends.
- **Real-Time Knowledge**: Accesses the latest news and specialized finance/news topics.
- **Web Fetch**: Extracts and cleans content from URLs for use as context in analysis tasks.

### Parallel Tool Execution
ChatPilot supports **parallel tool calls within a single agent step**, allowing multiple retrieval or research tools to run concurrently. This reduces latency, enables multi-source context gathering, and improves efficiency while preserving a single-agent architecture.

### Multi-LLM Flexibility
Built on **LangChain**, ChatPilot supports switching between top providers. Use the same agent with your preferred model provider:
- OpenAI 
- Anthropic 
- DeepSeek
- Google (Gemini)
- Local models via Ollama

---

## Tech Stack

- **Backend**: FastAPI (Python 3.10+)
- **Server**: Uvicorn (ASGI server with multi-worker support)
- **Agent Framework**: LangChain (Single-agent architecture with parallel tool execution)
- **Data Agent**: LangGraph (For iterative code execution and self-correction)
- **Vector Store**: ChromaDB
- **Embeddings & Reranking**: 
  - **Local Option**: HuggingFace embeddings (BAAI BGE-small-en-v1.5) + BGE reranker-v2-m3 (fully offline)
  - **Cloud Option**: Cohere API (1024D embeddings with reranking)
- **Containerization**: Docker (Secure code execution sandbox)
- **Document Processing**: Docling (Advanced document intelligence with OCR and bbox extraction)
- **Web Search**: Tavily API, Google Custom Search
- **Code Execution**: Isolated Docker sandbox with resource limits

---

## Getting Started

For detailed setup instructions including prerequisites, API key configuration, and Docker setup, see **[docs/SETUP.md](docs/SETUP.md)**.

**Quick Start:**
```bash
# 1. Clone and install dependencies
git clone https://github.com/Sreehari05055/ChatPilot.git
cd ChatPilot
pip install -r requirements.txt

# 2. Set up your .env file with API keys (see docs/SETUP.md)

# 3. Build Docker sandbox
docker build -t python-sandbox:latest -f Dockerfile .

# 4. Run the server
python main.py
```

Server runs on `http://localhost:8000` with 4 worker processes.

---

## License
Apache-2.0

````
