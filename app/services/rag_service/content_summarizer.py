from app.core.config import Config
from app import logger
from app.services.langchain_handler.langchain_service import LangChainService
from langchain_core.messages import SystemMessage, HumanMessage

class RAGSummarizer:
    def __init__(self):
        pass

    async def summarize(self, content, query):
        system_prompt = f"""
        ### ROLE
        You are a Lead Researcher. Your goal is to synthesize multiple data sources into a coherent, evidence-based answer.
        ### DATA SOURCES
        {content}

        ### INSTRUCTIONS
        1. SUMMARY: Provide a 2-3 sentence in-depth synthesis of the content. Explicitly link the findings to the user's specific query to show relevance.
        2. DETAILED ANALYSIS: Expand on the key facts, maintaining a neutral, academic tone.
        3. CITATION RULES: 
        - Use [Source: filename] for EVERY claim made. 
        - If multiple sources support a claim, list them all: [Source: A, Source: B].
        4. NEGATIVE CONSTRAINT: If the provided data does not contain the answer, explicitly state: "The current sources do not contain sufficient information to answer this." Do not use your internal knowledge."""
        
        query_str = ", ".join(query)                
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Questions: {query_str}")
        ]

        llm = LangChainService.get_llm(model_name=Config.MODEL_NAME)
        response = await llm.ainvoke(messages)
        return response.content