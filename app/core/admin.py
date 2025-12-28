"""
Admin configuration management
Handles model settings, tone/style, RAG parameters, and response formatting.
"""

from typing import Literal, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
import json
import os
from enum import Enum


class ToneStyle(str, Enum):
    """Available tone and style options for the chatbot."""
    FRIENDLY = "friendly"
    PROFESSIONAL = "professional"
    CONCISE = "concise"
    CREATIVE = "creative"

TONE_TEMPERATURES = {
    ToneStyle.FRIENDLY: 0.8,
    ToneStyle.PROFESSIONAL: 0.5,
    ToneStyle.CONCISE: 0.2,
    ToneStyle.CREATIVE: 1.1,
}

class ModelConfig(BaseModel):
    """Model configuration settings."""
    temperature: float = Field(default=0.4, ge=0.0, le=2.0, description="Model temperature (0-2)")
    top_p: float = Field(default=0.3, ge=0.0, le=1.0, description="Top-p sampling (0-1)")
    max_tokens: int = Field(default=1000, ge=1, le=4000, description="Maximum tokens to generate")

    def __init__(self, **data):
        super().__init__(**data)

class RAGConfig(BaseModel):
    """RAG (Retrieval-Augmented Generation) configuration."""
    chunk_size: int = Field(default=500, ge=100, le=4000, description="Text chunk size for indexing")
    chunk_overlap: int = Field(default=50, ge=0, le=1000, description="Overlap between chunks")
    top_k: int = Field(default=2, ge=1, le=10, description="Number of retrieved chunks")

class ChatbotConfig(BaseModel):
    """Complete chatbot configuration."""
    model: ModelConfig = Field(default_factory=ModelConfig)
    tone_style: ToneStyle = Field(default=ToneStyle.PROFESSIONAL)
    rag: RAGConfig = Field(default_factory=RAGConfig)
    max_conversation_turns: int = Field(default=10, ge=1, le=50, description="Max conversation history")
    model_config = dict(use_enum_values=True)


class AdminManager:
    """Manages chatbot configuration and settings."""
    
    def __init__(self, config_file: str = None):
        if config_file is None:
            config_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "configuration", "admin_config.json")
        self.config_file = config_file
        self.current_config = self._load_config()
    
    def _load_config(self) -> ChatbotConfig:
        """Load configuration from file or create default."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return ChatbotConfig(**data)
            except (json.JSONDecodeError, ValueError) as e:
                print(f"Error loading config: {e}. Using defaults.")
        
        return ChatbotConfig()
    
    def _save_config(self) -> bool:
        """Save current configuration to file."""
        try:
            config_dir = os.path.dirname(self.config_file)
            if config_dir:
                os.makedirs(config_dir, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.current_config.model_dump(), f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    def get_config(self) -> ChatbotConfig:
        """Get current configuration."""
        return self.current_config

    def update_model_config(self, **kwargs) -> bool:
        """Update model configuration."""
        try:
            current_model = self.current_config.model.model_dump()
            current_model.update(kwargs)
            self.current_config.model = ModelConfig(**current_model)
            return self._save_config()
        except Exception as e:
            print(f"Error updating model config: {e}")
            return False

    def update_rag_config(self, **kwargs) -> bool:
        """Update RAG configuration."""
        try:
            current_rag = self.current_config.rag.model_dump()
            current_rag.update(kwargs)
            self.current_config.rag = RAGConfig(**current_rag)
            return self._save_config()
        except Exception as e:
            print(f"Error updating RAG config: {e}")
            return False

    def update_style_config(self, tone_style: Optional[Union[ToneStyle]] = None) -> bool:
        """Update style and formatting configuration."""
        try:
            if tone_style is None:
                # Check if user changed default temperature
                tone = self.current_config.tone_style
            else:
                tone = tone_style

                        # Coerce raw_tone (which may be a string or ToneStyle) into a ToneStyle member
            try:
                if isinstance(tone, ToneStyle):
                    new_tone = tone
                else:
                    new_tone = ToneStyle(tone.lower())
            except Exception:
                new_tone = ToneStyle.PROFESSIONAL  # Fallback to current if invalid:
            
            self.current_config.tone_style = new_tone
            # Always set temperature to match tone
            self.current_config.model.temperature = TONE_TEMPERATURES.get(new_tone, ModelConfig().temperature)
            return self._save_config()
        except Exception as e:
            print(f"Error updating style config: {e}")
            return False
    
    def get_system_prompt_template(self) -> str:
        """Generate system prompt based on current configuration."""

        tone_style_instructions = {
                ToneStyle.FRIENDLY: {
                    "role_purpose": "You are a warm, approachable AI assistant who uses emojis, casual language, and friendly slang when appropriate. Your goal is to make users feel comfortable and engaged.",
                    "function_calling": "You can call the `research_wrapper` tool when users need info. Before calling, rephrase the user's query into a concise, well-formed tool input that focuses on keywords and intent (remove filler).",
                    "output_structure": "Use emojis, casual language, and friendly formatting. Make it feel like chatting with a helpful friend who knows their stuff!",
                    "strict_rules": "Be warm and encouraging. Use casual language and emojis appropriately. Make users feel comfortable asking questions.",
                    "style_tone": "Use emojis, be approachable, use friendly slang when appropriate, and make everything feel conversational and warm."
                },
                ToneStyle.PROFESSIONAL: {
                    "role_purpose": "You are a professional, authoritative AI assistant who communicates with precision and expertise. Your goal is to deliver accurate, well-structured business communications.",
                    "function_calling": "You can call the `research_wrapper` tool for additional information. When invoking the tool, rephrase the user's question succinctly as the tool input (focus on core terms and intent).",
                    "output_structure": "Use formal business formatting with clear headings, professional language, and structured layouts suitable for business communications.",
                    "strict_rules": "Maintain professional standards. Use formal language and business-appropriate terminology. Ensure accuracy and reliability.",
                    "style_tone": "Be formal, precise, and authoritative. Use business-appropriate language and maintain professional standards throughout."
                },
                ToneStyle.CONCISE: {
                    "role_purpose": "You are a direct, efficient AI assistant who gets straight to the point. Your goal is to deliver clear, brief answers without unnecessary elaboration.",
                    "function_calling": "You can call the `research_wrapper` tool when needed. Before calling, rephrase the user's question into a terse, precise tool input emphasizing keywords and removing filler.",
                    "output_structure": "Keep it brief and scannable. Use bullet points, short paragraphs, and get to the point immediately.",
                    "strict_rules": "Be direct and to the point. Avoid unnecessary words or elaboration. Focus on essential information only.",
                    "style_tone": "Be brief, direct, and efficient. Skip pleasantries and get straight to the answer."
                },
                ToneStyle.CREATIVE: {
                    "role_purpose": "You are an imaginative, engaging AI assistant who uses creative language and metaphors. Your goal is to make information interesting and memorable.",
                    "function_calling": "You can call the `research_wrapper` tool to explore topics. When doing so, succinctly rephrase the user's query into a clear tool input that highlights intent and key phrases (avoid flowery filler).",
                    "output_structure": "Use creative formatting, metaphors, and engaging language. Make information come alive with vivid descriptions and imaginative comparisons.",
                    "strict_rules": "Be creative and engaging. Use metaphors and vivid language to make information memorable and interesting.",
                    "style_tone": "Be imaginative, use metaphors, creative language, and make everything engaging and memorable."
                }
            }

        tone_instructions = tone_style_instructions[self.current_config.tone_style]
        
        function_calling_section = ""

        return f"""
                ROLE & PURPOSE  
                {tone_instructions['role_purpose']}
                
                CONTEXT USAGE  
                - You will receive the users conversation context and chat history.  
                - Always use them internally to understand the user's needs.  
                - Never mention, quote, or hint that they exist.  
                - Rephrase or summarize relevant details naturally into your answer without revealing their source.

                '''
                CONTEXT
                {{context}}
                '''

                OUTPUT STRUCTURE  
                {tone_instructions['output_structure']}
                1. **Main Answer** — Use bold, italics, bullet points, numbered lists, and emojis.  
                2. **Steps or Process** — Present in ordered lists when explaining actions.  
                3. **Tables** — Use valid Markdown table syntax (header + separator row).  
                4. **Code or Formulas** — Wrap in triple backticks (```) with language tag. Keep formulas on a single line.  
                5. **Related Questions** — End with 2–3 natural, relevant next questions (never label them as "follow-ups").  
                
                STRICT RULES  
                {tone_instructions['strict_rules']}
                - Always answer using the provided context & history.  
                - Focus entirely on the query; keep responses free of references to yourself, your capabilities, or the system.  
                - Format tables in Markdown or HTML, never using plain-text "pipes".  
                - When something is unclear, ask a concise and polite clarifying question.  
                - For sensitive data, respond respectfully and decline to proceed if it cannot be shared.

                STYLE & TONE  
                {tone_instructions['style_tone']}
                - Warm and approachable greeting if the user greets you  
                - Calm and supportive for confusion/frustration  
                - Concise and energetic for curiosity  
                - Empathetic and insightful at all times  
                - Stay entirely on the user's task
                """
    
    def export_config(self) -> Dict[str, Any]:
        """Export current configuration as dictionary."""
        return self.current_config.model_dump()
    
    def import_config(self, config_data: Dict[str, Any]) -> bool:
        """Import configuration from dictionary."""
        try:
            self.current_config = ChatbotConfig(**config_data)
            return self._save_config()
        except Exception as e:
            print(f"Error importing config: {e}")
            return False



