"""
Pydantic Schemas for Recommendation Responses and Explanations
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from backend.app.schemas.movie import MovieSummary


class RecommendationResponse(BaseModel):
    user_id: int
    algorithm: str = Field(..., example="ALS-Collaborative-Filtering")
    recommendations: List[MovieSummary]
    execution_time_ms: float = Field(..., example=3.45)
    explanation: Optional[str] = Field(None, example="Based on your high ratings for Sci-Fi and Action movies")


class SimilarMoviesResponse(BaseModel):
    source_movie_id: int
    similar_movies: List[MovieSummary]
