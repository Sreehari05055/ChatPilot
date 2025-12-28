import re
from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    research_mode: bool = False

    @field_validator('question')
    @classmethod
    def no_empty_or_whitespace(cls, v: str):
        v = re.sub(r'<[^>]+>', '', v)  # Remove HTML tags
        v = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', v)
        if not v.strip():
            raise ValueError('Question cannot be empty or whitespace')
        return v
