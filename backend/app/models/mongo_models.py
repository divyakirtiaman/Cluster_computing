"""
MongoDB Document Models
-----------------------
These Pydantic models represent the exact shape of documents stored in MongoDB.
They are NOT the same as API schemas (backend/app/schemas/) which define
HTTP request/response shapes.

Key design decisions:
- PyObjectId: MongoDB's native ObjectId cannot be serialized to JSON directly.
  We wrap it in a custom validator so FastAPI can convert it to a string.
- All timestamps are timezone-aware UTC datetimes (not naive datetimes).
- Optional fields use None defaults so partial documents are valid.

Document Model Hierarchy:
  MongoBaseModel          ← All documents share _id field
  ├── UserDocument        ← users collection
  ├── MovieDocument       ← movies collection
  ├── RatingDocument      ← ratings collection
  ├── ReviewDocument      ← reviews collection
  ├── WatchlistDocument   ← watchlists collection
  └── RecommendationHistoryDocument  ← recommendation_history collection
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any, List, Optional

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Custom ObjectId type for Pydantic v2
# ---------------------------------------------------------------------------
# MongoDB uses a 12-byte BSON ObjectId as the primary key (stored as _id).
# Pydantic v2 doesn't know about ObjectId natively, so we:
#   1. Store the _id as a Python string in our model (simpler serialization).
#   2. Use a @field_validator to convert ObjectId → str when loading from DB.
# ---------------------------------------------------------------------------

def _now_utc() -> datetime:
    """Return current UTC time with timezone info (not deprecated utcnow)."""
    return datetime.now(timezone.utc)


class MongoBaseModel(BaseModel):
    """
    Base class for all MongoDB document models.
    Configures Pydantic to:
      - Accept population by field name AND alias (needed for _id → id mapping)
      - Allow arbitrary types (ObjectId)
      - Serialize ObjectId as string in JSON output
    """
    model_config = ConfigDict(
        populate_by_name=True,       # allow both "id" and "_id" field names
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
    )

    id: Optional[str] = Field(default=None, alias="_id")

    @field_validator("id", mode="before")
    @classmethod
    def coerce_object_id(cls, v: Any) -> Optional[str]:
        """Convert ObjectId instances to str automatically."""
        if isinstance(v, ObjectId):
            return str(v)
        return v


# ---------------------------------------------------------------------------
# users collection
# ---------------------------------------------------------------------------
class UserDocument(MongoBaseModel):
    """
    Represents one document in the 'users' collection.

    MongoDB document shape:
    {
        "_id":              ObjectId("..."),
        "email":            "alice@example.com",
        "username":         "alice_wonder",
        "hashed_password":  "$2b$12$...",
        "preferred_genres": ["Sci-Fi", "Adventure"],
        "is_active":        true,
        "is_superuser":     false,
        "created_at":       ISODate("2024-01-15T10:00:00Z"),
        "updated_at":       ISODate("2024-01-15T10:00:00Z")
    }
    """
    email: str
    username: str
    hashed_password: str
    preferred_genres: List[str] = Field(default_factory=list)
    is_active: bool = True
    is_superuser: bool = False
    created_at: datetime = Field(default_factory=_now_utc)
    updated_at: datetime = Field(default_factory=_now_utc)
    total_ratings: int = 0          # denormalized counter — updated on each rating


# ---------------------------------------------------------------------------
# movies collection
# ---------------------------------------------------------------------------
class MovieDocument(MongoBaseModel):
    """
    Represents one document in the 'movies' collection.

    'movie_id' is the original MovieLens integer ID (1–1682).
    It is indexed as a unique field, separate from MongoDB's _id.

    MongoDB document shape:
    {
        "_id":          ObjectId("..."),
        "movie_id":     50,
        "title":        "Star Wars (1977)",
        "genres":       ["Action", "Adventure", "Sci-Fi"],
        "release_year": 1977,
        "imdb_url":     "http://us.imdb.com/M/title-exact?Star%20Wars%20(1977)",
        "avg_rating":   4.36,
        "total_ratings": 584,
        "popularity_score": 0.0
    }
    """
    movie_id: int                              # MovieLens integer ID
    title: str
    genres: List[str] = Field(default_factory=list)
    release_year: Optional[int] = None
    imdb_url: Optional[str] = None
    avg_rating: float = 0.0                   # denormalized — updated incrementally
    total_ratings: int = 0                    # denormalized rating count
    popularity_score: float = 0.0             # precomputed for ranking


# ---------------------------------------------------------------------------
# ratings collection
# ---------------------------------------------------------------------------
class RatingDocument(MongoBaseModel):
    """
    Represents one document in the 'ratings' collection.

    The (user_id, movie_id) pair has a UNIQUE compound index — a user can
    only rate each movie once (subsequent submissions overwrite via upsert).

    MongoDB document shape:
    {
        "_id":       ObjectId("..."),
        "user_id":   "507f1f77bcf86cd799439011",   ← string ObjectId ref to users
        "movie_id":  50,                             ← MovieLens integer ID
        "rating":    4.5,
        "rated_at":  ISODate("2024-02-01T14:30:00Z")
    }
    """
    user_id: str                               # string ref to users._id
    movie_id: int                              # MovieLens integer ID
    rating: float                              # 1.0 to 5.0
    rated_at: datetime = Field(default_factory=_now_utc)


# ---------------------------------------------------------------------------
# reviews collection
# ---------------------------------------------------------------------------
class ReviewDocument(MongoBaseModel):
    """
    Represents one document in the 'reviews' collection.

    Reviews are free-text annotations attached to a rating.
    Sentiment is computed at write time by an NLP model (Phase 10).

    MongoDB document shape:
    {
        "_id":        ObjectId("..."),
        "user_id":    "507f1f77bcf86cd799439011",
        "movie_id":   50,
        "review_text": "An absolute classic. The Force is strong with this one.",
        "sentiment":  "positive",   ← "positive" | "negative" | "neutral"
        "created_at": ISODate("2024-02-01T14:35:00Z"),
        "updated_at": ISODate("2024-02-01T14:35:00Z")
    }
    """
    user_id: str
    movie_id: int
    review_text: str
    sentiment: Optional[str] = None           # filled in by NLP service (Phase 10)
    created_at: datetime = Field(default_factory=_now_utc)
    updated_at: datetime = Field(default_factory=_now_utc)


# ---------------------------------------------------------------------------
# watchlists collection
# ---------------------------------------------------------------------------
class WatchlistDocument(MongoBaseModel):
    """
    Represents one document in the 'watchlists' collection.

    Each document is one (user, movie) pair. The unique compound index
    prevents the same movie from being added twice.

    MongoDB document shape:
    {
        "_id":      ObjectId("..."),
        "user_id":  "507f1f77bcf86cd799439011",
        "movie_id": 50,
        "added_at": ISODate("2024-02-01T15:00:00Z")
    }
    """
    user_id: str
    movie_id: int
    added_at: datetime = Field(default_factory=_now_utc)


# ---------------------------------------------------------------------------
# recommendation_history collection
# ---------------------------------------------------------------------------
class RecommendationHistoryDocument(MongoBaseModel):
    """
    Represents one document in the 'recommendation_history' collection.

    Logs what was recommended to a user and when, for auditability and
    for future A/B testing analysis.

    MongoDB document shape:
    {
        "_id":                   ObjectId("..."),
        "user_id":               "507f1f77bcf86cd799439011",
        "algorithm":             "als_collaborative_filtering",
        "recommended_movie_ids": [50, 172, 181, 258, 269],
        "generated_at":          ISODate("2024-02-01T16:00:00Z"),
        "metadata": {
            "model_version": "v1.0",
            "latency_ms": 4.2
        }
    }
    """
    user_id: str
    algorithm: str                             # e.g. "als_collaborative_filtering"
    recommended_movie_ids: List[int] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=_now_utc)
    metadata: dict = Field(default_factory=dict)  # arbitrary algorithm metadata
