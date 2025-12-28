# ChatPilot Setup Guide

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- OpenAI API key (required)
- Google Cloud Custom Search API key + CSE ID (optional, for web search)

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

### 3. Add documents for RAG (optional)

To use the RAG (document Q&A) feature, add your documents to the `source_files/` directory:
```bash
# Add your PDFs, text files, or documents here
cp your_documents.pdf source_files/
cp your_notes.txt source_files/
```

Supported formats: PDF, TXT, DOCX, MD

The system will automatically index these documents when you start the server.

### 4. Configure ChatPilot
ChatPilot includes an interactive configuration wizard:
```bash
python main.py --configure
```
This will guide you through:
- Adding your LLM API key
- Choosing whether to enable web search
- If enabled, adding Google Custom Search API key and CSE ID

The wizard creates a `.env` file with your settings automatically.

### 5. Run ChatPilot

**Development mode (recommended for pre-release):**
```bash
python main.py --dev
```

## Configuration Options

### Interactive Configuration (`--configure`)

Sets up your API keys and enables/disables features:
```bash
python main.py --configure
```

**What it configures:**
- **LLM API key** (required)
- **Web search toggle** (optional)
  - If enabled, you'll need:
    - Google Custom Search API key
    - Custom Search Engine ID (CSE ID)

### Admin Configuration (`--admin-config`)

Customize ChatPilot's behavior and model settings:
```bash
python main.py --admin-config
```
**Available settings:**

**Model Configuration:**
- Model selection (gpt-5.2, gpt-5, gpt-5-mini, gpt-4.1, gpt-4.1-mini, gpt-4o, gpt-4o-mini, etc)
- Temperature (0.0 - 2.0) - controls response randomness
- Top-p (0.0 - 1.0) - nucleus sampling parameter
- Max tokens - maximum response length

**System Behavior:**
- Character/tone (friendly, professional, concise, creative)

**RAG Settings:**
- Text chunk size - how documents are split for embedding
- Chunk overlap - overlap between chunks for better context
- Number of chunks to retrieve - how many relevant chunks to use per query
- Max conversation turns - how much chat history to keep in context
- Maximum history messages - limit on stored conversation length


## Usage

### Starting the development server
```bash
python main.py --dev
```

Server runs on `http://localhost:8000` with auto-reload.

### Adding/updating documents for RAG

Simply add or remove files from the `source_files/` directory and restart the server. The documents will be re-indexed automatically.

### Reconfigure settings

**Update API keys or toggle features:**
```bash
python main.py --configure
```

**Adjust model and behavior settings:**
```bash
python main.py --admin-config
```