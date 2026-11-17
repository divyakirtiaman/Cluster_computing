"""
Pydantic Schemas for Movie entities and catalog responses
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class MovieBase(BaseModel):
    title: str = Field(..., example="Toy Story (1995)")
    release_date: Optional[str] = Field(None, example="01-Jan-1995")
    genres: List[str] = Field(default_factory=list, example=["Animation", "Children's", "Comedy"])
    imdb_url: Optional[str] = None
    poster_url: Optional[str] = None


class MovieCreate(MovieBase):
    movie_id: int


class MovieResponse(MovieBase):
    movie_id: int
    average_rating: Optional[float] = Field(0.0, example=4.15)
    total_ratings: Optional[int] = Field(0, example=452)

    class Config:
        from_attributes = True


class MovieSummary(BaseModel):
    movie_id: int
    title: str
    genres: List[str]
    poster_url: Optional[str] = None
    predicted_rating: Optional[float] = None
