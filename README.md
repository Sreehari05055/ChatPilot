# ✈️ ChatPilot

ChatPilot is a tool-augmented **Agentic Copilot** that goes beyond simple chat. It utilizes a single AI agent to interact with your local files, conduct deep web research, and perform autonomous data analysis through Python code execution.
z
**Demo Frontend:** [ChatPilot Frontend](https://github.com/Sreehari05055/Demo-frontend)

---

## 🚀 Key Capabilities

### 🧠 Agentic Document Search (RAG)
Upload PDFs, text files, or Word documents and ask questions. ChatPilot doesn't just retrieve text; it use tools to find and synthesize answers directly from your private knowledge base.

### 📊 Autonomous Data Analysis
Upload CSV or Excel files and ask for insights. ChatPilot functions as a **Data Analyst Agent**:
- **Planning**: Formulates a step-by-step analysis strategy.
- **Execution**: Writes and runs Python code in a secure sandbox.
- **Self-Correction**: If the code fails, the agent analyzes the error and automatically retries until it gets the result.

### 🌐 Smart Web Research
Powered by **Tavily** and **Google Search**, the agent can:
- **Search**: Stay updated with real-time news and general knowledge.
- **Deep Research**: Conduct multi-source deep dives to generate comprehensive reports.
- **Web Fetch**: Extract and clean content from specific URLs to process them as context.

### 🔓 Multi-LLM Flexibility
Built on **LangChain**, ChatPilot supports switching between top providers. Use the same agent with your preferred model provider:
- OpenAI 
- Anthropic 
- DeepSeek
- Google (Gemini)
- Local models via Ollama

---

## 🛠️ Tech Stack

- **Backend**: FastAPI (Python 3.10+)
- **Orchestration**: LangChain (Full tool-calling support)
- **Data Agent**: LangGraph (For iterative code execution and self-correction)
- **Vector Store**: ChromaDB
- **Tools**: Tavily API, Google Custom Search, Python Sandbox

---

## 🏁 Getting Started

1. **Setup Environment**:
   Copy `.env.example` to `.env` and add your API keys.
   ```bash
   cp .env.example .env
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the Server**:
   ```bash
   uvicorn app.main:app --reload
   ```

---

## 📜 License
Apache-2.0
