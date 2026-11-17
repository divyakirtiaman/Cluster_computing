"""
API v1 Router Aggregator
Combines sub-routers for auth, movies, recommendations, and ratings.
"""

from fastapi import APIRouter
from backend.app.api.v1.endpoints import auth, movies, recommendations, ratings, watchlist

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(movies.router, prefix="/movies", tags=["Movies"])
api_router.include_router(recommendations.router, prefix="/recommendations", tags=["Recommendations"])
api_router.include_router(ratings.router, prefix="/ratings", tags=["Ratings"])
api_router.include_router(watchlist.router, prefix="/watchlist", tags=["Watchlist"])
