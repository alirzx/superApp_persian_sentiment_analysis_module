from typing import Literal
from pydantic import BaseModel, Field, field_validator

class TextRequest(BaseModel):
    text: str = Field(min_length=1)
    request_id: str | None = Field(default=None, max_length=100)

    @field_validator("text")
    @classmethod
    def check_text(cls, v):
        if not v.strip():
            raise ValueError("Text must not be blank")
        return v

class BatchRequest(BaseModel):
    task: Literal["sentiment", "topics"]
    texts: list[str] = Field(min_length=1)
    request_id: str | None = Field(default=None, max_length=100)

    @field_validator("texts")
    @classmethod
    def check_texts(cls, v):
        if any(not s.strip() for s in v):
            raise ValueError("Batch includes empty text")
        return v
