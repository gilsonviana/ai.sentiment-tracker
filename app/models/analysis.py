from pydantic import BaseModel
from typing import Optional

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
