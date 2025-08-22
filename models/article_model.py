from pydantic import BaseModel, Field
from typing import List

class ArticleModel(BaseModel):
    news: str = Field(..., description="News")
    published_date: str = Field(..., description="published date")
    impacts_instruments: List[str] = Field(..., description="List of impacted instruments, currency pairs, or commodities")