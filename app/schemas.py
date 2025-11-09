from pydantic import BaseModel
from datetime import datetime

class WeatherOut(BaseModel):
    city: str
    units: str
    temperature: float | None = None
    description: str | None = None
    from_cache: bool = False
    created_at: datetime

class HistoryItem(WeatherOut):
    id: int

class HistoryPage(BaseModel):
    page: int
    per_page: int
    total: int
    items: list[HistoryItem]
