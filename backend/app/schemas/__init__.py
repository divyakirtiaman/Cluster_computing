"""
Schemas Package
"""
from backend.app.schemas.movie import MovieBase, MovieCreate, MovieResponse, MovieSummary
from backend.app.schemas.user import UserBase, UserCreate, UserLogin, TokenResponse, UserResponse
from backend.app.schemas.recommendation import RecommendationResponse, SimilarMoviesResponse

__all__ = [
    "MovieBase", "MovieCreate", "MovieResponse", "MovieSummary",
    "UserBase", "UserCreate", "UserLogin", "TokenResponse", "UserResponse",
    "RecommendationResponse", "SimilarMoviesResponse"
]
