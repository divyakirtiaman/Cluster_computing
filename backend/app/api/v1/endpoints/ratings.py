"""
Ratings & Feedback API Endpoints
Handles user ratings, MongoDB persistence, and automatic Redis cache invalidation.
"""

import logging
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from backend.app.core.cache import cache_service
from backend.app.core.database import is_mongo_connected, _database
from backend.app.repositories.rating_repository import RatingRepository

logger = logging.getLogger("cinematch.ratings")
router = APIRouter()


class RatingSubmission(BaseModel):
    user_id: int = Field(..., example=1)
    movie_id: int = Field(..., example=50)
    rating: float = Field(..., ge=1.0, le=5.0, example=4.5)


class RatingResponse(BaseModel):
    status: str
    message: str
    user_id: int
    movie_id: int
    rating: float
    cache_invalidated: bool
    persisted_to_db: bool


@router.post("/", response_model=RatingResponse, status_code=status.HTTP_201_CREATED)
async def submit_rating(submission: RatingSubmission):
    """
    Submits or updates a user rating for a movie:
      1. Persists/upserts rating to MongoDB ratings collection (if connected).
      2. Invalidates user's cached recommendation entries in Redis so next query reranks.
      3. Invalidates movie cache to refresh aggregate stats.
    """
    persisted = False
    if is_mongo_connected() and _database is not None:
        try:
            repo = RatingRepository(_database)
            await repo.upsert_rating(
                user_id=str(submission.user_id),
                movie_id=submission.movie_id,
                rating=submission.rating
            )
            persisted = True
            logger.info("Persisted rating in MongoDB: user=%s, movie=%s, rating=%s",
                        submission.user_id, submission.movie_id, submission.rating)
        except Exception as exc:
            logger.warning("Failed to persist rating to MongoDB: %s", exc)

    # Invalidate Redis caches
    invalidated_count = await cache_service.invalidate_user_recommendations(submission.user_id)
    await cache_service.invalidate_movie_cache(submission.movie_id)

    return RatingResponse(
        status="success",
        message=f"Rating of {submission.rating} recorded for movie {submission.movie_id} by user {submission.user_id}",
        user_id=submission.user_id,
        movie_id=submission.movie_id,
        rating=submission.rating,
        cache_invalidated=True,
        persisted_to_db=persisted
    )
