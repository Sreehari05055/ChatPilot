# ChatPilot

Chat with your documents, search the web, and analyze data files - all in one place.

**Demo Frontend:** Try ChatPilot with a UI → [ChatPilot Frontend](https://github.com/Sreehari05055/Demo-frontend)

## What it does

Upload files and ask questions. ChatPilot can:

- **Search your documents** (RAG) - Upload PDFs, text files, docs and ask questions. Gets answers from your files.
- **Search the web** - Pulls in current information and fetches specific URLs when needed.
- **Analyze data** - Upload CSV/Excel files and ask for analysis. Writes and runs Python code automatically to get you answers.

All of this works in a normal conversation. Ask follow-ups, combine different sources, whatever you need.

## How it works

- Built with FastAPI and async streaming
- Currently supports OpenAI models (Claude, DeepSeek, and Gemini support coming soon)
- Uses vector search for documents
- Runs Python code in a sandbox for data analysis
- Keeps conversation history so you can ask follow-ups naturally

## Examples

- "What does the report say about Q3 revenue?"
- "Find the ship with highest engine efficiency" (from CSV)
- "What's the latest Python release?" (web search)
- Upload docs + ask "How does this compare to industry standards?" (uses both files and web)
- "Build a model to predict customer churn" (does EDA, preprocessing, trains model, saves pipeline)

## Setup

- Check the docs/ directory for setup and installation instructions.

## Tech

- FastAPI backend with streaming
- Vector database for document search
- Sandboxed Python execution for data analysis
- Multi-LLM support (OpenAI/Claude/DeepSeek)
- Tool system for web search and code execution

## License

Apache-2.0
