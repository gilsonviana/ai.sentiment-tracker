from datetime import datetime
from pydantic import BaseModel


class ReflectionResponse(BaseModel):
    narrative: str
    entry_count: int
    avg_mood: float
    window_start: str
    window_end: str


class StoredReflection(BaseModel):
    id: str
    narrative: str
    entry_count: int
    avg_mood: float
    window_start: str
    window_end: str
    generated_at: datetime
