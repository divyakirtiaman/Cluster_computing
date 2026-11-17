"""
Rating Repository
-----------------
All MongoDB operations for the 'ratings' collection.

The ratings collection is the most write-heavy collection in CineMatch.
Key design decisions:
  - UPSERT pattern: a user can only have one rating per movie.
    If they rate again, the old rating is overwritten (not duplicated).
  - Aggregation pipeline: MongoDB's $group + $avg stages compute
    per-user and per-movie statistics directly in the database.
"""

from datetime import datetime, timezone
from typing import List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from backend.app.models.mongo_models import RatingDocument


class RatingRepository:
    """
    Encapsulates all MongoDB operations for the ratings collection.
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db["ratings"]

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    async def find_by_user(self, user_id: str, limit: int = 100) -> List[RatingDocument]:
        """
        Fetch all ratings submitted by a specific user.
        Uses the index on user_id — fast even with 100k+ ratings total.
        """
        cursor = self.collection.find({"user_id": user_id}).limit(limit)
        docs = await cursor.to_list(length=limit)
        return [RatingDocument(**doc) for doc in docs]

    async def find_by_movie(self, movie_id: int, limit: int = 100) -> List[RatingDocument]:
        """Fetch all ratings for a specific movie. Uses the movie_id index."""
        cursor = self.collection.find({"movie_id": movie_id}).limit(limit)
        docs = await cursor.to_list(length=limit)
        return [RatingDocument(**doc) for doc in docs]

    async def find_one(self, user_id: str, movie_id: int) -> Optional[RatingDocument]:
        """Look up the specific rating a user gave to a movie. Returns None if unrated."""
        doc = await self.collection.find_one({"user_id": user_id, "movie_id": movie_id})
        return RatingDocument(**doc) if doc else None

    async def get_user_rating_stats(self, user_id: str) -> dict:
        """
        Aggregation pipeline: compute rating statistics for a user.

        Pipeline stages:
          $match  → filter to only this user's documents
          $group  → group ALL matched docs into one, computing:
                    count, avg, min, max rating values

        Returns a dict: {"count": int, "avg": float, "min": float, "max": float}
        or empty dict if user has no ratings.
        """
        pipeline = [
            {"$match": {"user_id": user_id}},
            {
                "$group": {
                    "_id": "$user_id",
                    "count":   {"$sum": 1},
                    "avg":     {"$avg": "$rating"},
                    "min_val": {"$min": "$rating"},
                    "max_val": {"$max": "$rating"},
                }
            },
        ]
        results = await self.collection.aggregate(pipeline).to_list(length=1)
        if not results:
            return {}
        r = results[0]
        return {
            "count":   r["count"],
            "avg":     round(r["avg"], 2),
            "min":     r["min_val"],
            "max":     r["max_val"],
        }

    # ------------------------------------------------------------------
    # WRITE
    # ------------------------------------------------------------------

    async def upsert_rating(self, user_id: str, movie_id: int, rating: float) -> RatingDocument:
        """
        Insert or update a rating (upsert = update if exists, insert if not).

        MongoDB upsert mechanics:
          filter:  {"user_id": ..., "movie_id": ...}
          update:  $set all fields
          upsert=True: if no document matches the filter, insert a new one

        The unique compound index on (user_id, movie_id) guarantees only one
        rating document per user/movie pair exists at all times.

        Returns the final document (after upsert).
        """
        now = datetime.now(timezone.utc)
        updated = await self.collection.find_one_and_update(
            {"user_id": user_id, "movie_id": movie_id},
            {
                "$set": {
                    "rating":   rating,
                    "rated_at": now,
                    # setOnInsert only runs when a NEW document is created
                    # (not on update) — sets user_id/movie_id on first insert
                },
                "$setOnInsert": {
                    "user_id":  user_id,
                    "movie_id": movie_id,
                },
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return RatingDocument(**updated)

    async def bulk_insert(self, ratings: List[RatingDocument]) -> int:
        """
        Bulk insert ratings (used by the database seeder script).
        ordered=False allows skipping duplicates without halting the batch.
        Returns count of successfully inserted documents.
        """
        if not ratings:
            return 0
        docs = [r.model_dump(exclude={"id"}, by_alias=False) for r in ratings]
        try:
            result = await self.collection.insert_many(docs, ordered=False)
            return len(result.inserted_ids)
        except Exception:
            # BulkWriteError is raised when some docs fail (e.g. duplicates)
            # but the rest succeed. We return 0 to signal caller to check logs.
            return 0
