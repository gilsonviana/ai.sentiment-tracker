from pydantic import BaseModel


class MoodDataPoint(BaseModel):
    date: str
    score: float
    label: str


class MoodReport(BaseModel):
    month: str
    entries: list[MoodDataPoint]
    avg_mood: float
    entry_count: int
