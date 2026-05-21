from pydantic import BaseModel


class ReflectionResponse(BaseModel):
    narrative: str
    entry_count: int
    avg_mood: float
