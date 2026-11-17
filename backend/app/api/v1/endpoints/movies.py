"""
Movie Catalog Endpoints (Search, Details, Genre Filtering)
Powered by clean MovieLens 100K catalog in-memory lookups.
"""

from typing import List, Optional
from fastapi import APIRouter, Query, HTTPException, status
from backend.app.schemas.movie import MovieResponse
from backend.app.services.recsys_service import recsys_service

router = APIRouter()


@router.get("/", response_model=List[MovieResponse])
async def list_movies(
    genre: Optional[str] = Query(None, description="Filter by genre (e.g. Action, Comedy, Sci_Fi)"),
    search: Optional[str] = Query(None, description="Case-insensitive title search"),
    limit: int = Query(24, ge=1, le=100, description="Number of titles to return")
):
    """Lists movies with optional text search and genre filtering."""
    return await recsys_service.list_movies(genre=genre, search=search, limit=limit)


@router.get("/genres", response_model=List[str])
async def list_genres():
    """Returns all available distinct movie genres in the catalog."""
    return recsys_service.get_genres()


@router.get("/{movie_id}", response_model=MovieResponse)
async def get_movie(movie_id: int):
    """Fetches details for a single movie by its MovieLens ID."""
    movie = await recsys_service.get_movie_by_id(movie_id)
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Movie with ID {movie_id} was not found in catalog"
        )
    return movie
