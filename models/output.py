"""
Output model for crawled articles.

This module defines the output model for storing crawled articles.
"""
from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime


class OutputModel(BaseModel):
    """Model for storing crawled articles."""
    
    title: str
    publishDate: datetime
    publishDatePst: Optional[datetime] = None
    content: str
    url: str
    source: Optional[str] = None
    author: Optional[str] = None
    category: Optional[str] = None
    crawled_at: Optional[str] = None
    article_id: Optional[str] = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert the model to a dictionary, converting datetimes to ISO strings."""
        return {
            "title": self.title,
            "publishDate": self.publishDate.isoformat() if self.publishDate else None,
            "publishDatePst": self.publishDatePst.isoformat() if self.publishDatePst else None,
            "content": self.content,
            "url": self.url,
            "source": self.source,
            "author": self.author,
            "category": self.category,
            "crawled_at": self.crawled_at,
            "article_id": self.article_id
        }