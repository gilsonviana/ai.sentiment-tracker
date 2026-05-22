from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class SentimentResult(BaseModel):
    vader_score: float        # compound score: -1.0 to 1.0
    roberta_score: float      # normalised: -1.0 to 1.0
    composite_score: float    # average of the two
    label: str                # "positive" | "neutral" | "negative"

class AnalysisResult(BaseModel):
    entry_id: str
    sentiment: SentimentResult
    entities: list[str]       # ["work", "Alice", "London", ...]
    embedding: list[float]    # 384-dim vector (not stored in SQLite, goes to Chroma)

class AnalysisResponse(BaseModel):
    entry_id: str
    vader_score: float
    roberta_score: float
    composite_score: float
    label: str
    entities: list[str]
    analysed_at: datetime
