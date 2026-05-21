from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional
import uuid

class JournalEntryCreate(BaseModel):
    """Payload the client sends to POST /entries."""
    content: str = Field(..., min_length=1, max_length=5000)

    @field_validator("content")
    @classmethod
    def strip_content(cls, v: str) -> str:
        return v.strip()

class JournalEntryDB(BaseModel):
    """Row shape returned from SQLite."""
    id: str
    content: str
    created_at: datetime
    status: str  # "pending" | "processed" | "failed"

class JournalEntryResponse(BaseModel):
    """What the API returns after a POST."""
    id: str
    status: str
    created_at: datetime
