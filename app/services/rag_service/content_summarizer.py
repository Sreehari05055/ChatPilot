from app.core.config import Config
from app import logger

class RAGSummarizer:
    def __init__(self, llm_engine):
        self.llm_engine = llm_engine

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
                                
        messages = [{"role": "user", "content": query}]

        response = await self.llm_engine._gpt_engine_stream(messages=messages, system_prompt=system_prompt, model=Config.MODEL_NAME, top_p=Config.TOP_P, max_completion_tokens=Config.MAX_TOKENS, temperature=Config.TEMPERATURE, stream=False, use_tools=False)
        
        logger.info(f"generated response: {response}")

        return response