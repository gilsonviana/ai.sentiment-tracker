import re
from datetime import datetime, date

from pydantic import BaseModel, Field, field_validator


class JournalEntryCreate(BaseModel):
    """Payload the client sends to POST /entries."""
    content: str = Field(..., min_length=1, max_length=5000)
    entry_date: date | None = None  # defaults to today in save_entry if omitted

    @field_validator("content")
    @classmethod
    def strip_and_check_content(cls, v: str) -> str:
        v = v.strip()
        if not re.search(r"[a-zA-Z]", v):
            raise ValueError("Entry must contain at least one word")
        return v

class JournalEntryDB(BaseModel):
    """Row shape returned from SQLite."""
    id: str
    content: str
    created_at: datetime
    entry_date: date
    status: str  # "pending" | "processed" | "failed"

class JournalEntryResponse(BaseModel):
    """What the API returns after a POST."""
    id: str
    content: str
    status: str
    created_at: datetime
    entry_date: date
