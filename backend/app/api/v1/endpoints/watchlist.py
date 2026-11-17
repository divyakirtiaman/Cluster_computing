"""
Watchlist API Endpoints
Allows users to save movies to their watchlist, retrieve their list, and remove items.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.app.core.database import is_mongo_connected, _database
from backend.app.repositories.watchlist_repository import WatchlistRepository
from backend.app.schemas.movie import MovieResponse
from backend.app.services.recsys_service import recsys_service

router = APIRouter()

# In-memory fallback watchlist store when MongoDB is offline
_in_memory_watchlists: dict = {}


class WatchlistRequest(BaseModel):
    user_id: int = Field(..., example=1)
    movie_id: int = Field(..., example=50)


class WatchlistResponse(BaseModel):
    status: str
    message: str
    user_id: int
    movie_id: int
    in_watchlist: bool


@router.get("/{user_id}", response_model=List[MovieResponse])
async def get_user_watchlist(user_id: int):
    """
    Returns the full list of movies in the user's watchlist with catalog details.
    """
    movie_ids = []
    if is_mongo_connected() and _database is not None:
        try:
            repo = WatchlistRepository(_database)
            movie_ids = await repo.get_user_watchlist(str(user_id))
        except Exception:
            movie_ids = _in_memory_watchlists.get(user_id, [])
    else:
        movie_ids = _in_memory_watchlists.get(user_id, [])

    movies = []
    for mid in movie_ids:
        movie = await recsys_service.get_movie_by_id(mid)
        if movie:
            movies.append(movie)

    return movies


@router.post("/", response_model=WatchlistResponse, status_code=status.HTTP_201_CREATED)
async def add_to_watchlist(payload: WatchlistRequest):
    """
    Adds a movie to the user's personal watchlist.
    """
    added = True
    if is_mongo_connected() and _database is not None:
        try:
            repo = WatchlistRepository(_database)
            added = await repo.add_movie(str(payload.user_id), payload.movie_id)
        except Exception:
            pass

    if payload.user_id not in _in_memory_watchlists:
        _in_memory_watchlists[payload.user_id] = []
    if payload.movie_id not in _in_memory_watchlists[payload.user_id]:
        _in_memory_watchlists[payload.user_id].append(payload.movie_id)

    return WatchlistResponse(
        status="success" if added else "already_present",
        message=f"Movie {payload.movie_id} added to watchlist for user {payload.user_id}",
        user_id=payload.user_id,
        movie_id=payload.movie_id,
        in_watchlist=True
    )


@router.delete("/{user_id}/{movie_id}", response_model=WatchlistResponse)
async def remove_from_watchlist(user_id: int, movie_id: int):
    """
    Removes a movie from the user's personal watchlist.
    """
    if is_mongo_connected() and _database is not None:
        try:
            repo = WatchlistRepository(_database)
            await repo.remove_movie(str(user_id), movie_id)
        except Exception:
            pass

    if user_id in _in_memory_watchlists:
        _in_memory_watchlists[user_id] = [m for m in _in_memory_watchlists[user_id] if m != movie_id]

    return WatchlistResponse(
        status="success",
        message=f"Movie {movie_id} removed from watchlist",
        user_id=user_id,
        movie_id=movie_id,
        in_watchlist=False
    )
