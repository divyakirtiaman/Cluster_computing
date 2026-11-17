"""
Movie Repository
-----------------
All MongoDB operations for the 'movies' collection.
Routes call these methods — no raw pymongo/motor code in route handlers.

Pattern: Repository = "Data Access Object" for one collection.
  - Accepts: primitive Python types (int, str, list)
  - Returns: Pydantic document models or None
  - Raises:  motor exceptions bubble up to the route layer

Collection indexes (created at startup in database.py):
  - movie_id (unique)   → fast lookup by MovieLens ID
  - title TEXT          → full-text search via $text operator
"""

from typing import List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import DESCENDING, ReturnDocument

from backend.app.models.mongo_models import MovieDocument


class MovieRepository:
    """
    Encapsulates all MongoDB CRUD and query operations for the movies collection.
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        # Motor collection handle — all await calls go through this
        self.collection = db["movies"]

    # ------------------------------------------------------------------
    # READ operations
    # ------------------------------------------------------------------

    async def find_by_movie_id(self, movie_id: int) -> Optional[MovieDocument]:
        """
        Look up a movie by its MovieLens integer ID.
        Uses the unique index on 'movie_id' — O(log n) lookup.
        """
        doc = await self.collection.find_one({"movie_id": movie_id})
        if doc is None:
            return None
        return MovieDocument(**doc)

    async def find_many(
        self,
        skip: int = 0,
        limit: int = 20,
        genre: Optional[str] = None,
        min_rating: Optional[float] = None,
    ) -> List[MovieDocument]:
        """
        Paginated movie listing with optional genre and rating filters.

        Args:
            skip:       number of documents to skip (pagination offset)
            limit:      max documents to return (page size)
            genre:      filter to movies containing this genre string
            min_rating: only return movies with avg_rating >= min_rating

        MongoDB query breakdown:
            {"genres": genre}   → array field contains the genre string
            {"avg_rating": {"$gte": min_rating}}  → gte = greater than or equal
        """
        query: dict = {}
        if genre:
            query["genres"] = genre                     # array contains element
        if min_rating is not None:
            query["avg_rating"] = {"$gte": min_rating}

        cursor = (
            self.collection.find(query)
            .sort("popularity_score", DESCENDING)       # most popular first
            .skip(skip)
            .limit(limit)
        )
        docs = await cursor.to_list(length=limit)
        return [MovieDocument(**doc) for doc in docs]

    async def search_by_title(self, query: str, limit: int = 10) -> List[MovieDocument]:
        """
        Full-text search on the 'title' field using MongoDB's $text operator.

        The TEXT index on 'title' tokenizes words, removes stop words, and
        stems them so "wars" matches "Star Wars (1977)".

        Results are sorted by relevance score (textScore) — highest first.
        """
        cursor = (
            self.collection.find(
                {"$text": {"$search": query}},
                {"score": {"$meta": "textScore"}}       # include relevance score
            )
            .sort([("score", {"$meta": "textScore"})])  # sort by relevance
            .limit(limit)
        )
        docs = await cursor.to_list(length=limit)
        return [MovieDocument(**doc) for doc in docs]

    async def find_by_ids(self, movie_ids: List[int]) -> List[MovieDocument]:
        """
        Batch fetch multiple movies by their MovieLens IDs.
        Uses $in operator — single round-trip to MongoDB.
        Returns in arbitrary order (caller sorts if needed).
        """
        cursor = self.collection.find({"movie_id": {"$in": movie_ids}})
        docs = await cursor.to_list(length=len(movie_ids))
        return [MovieDocument(**doc) for doc in docs]

    async def count(self, genre: Optional[str] = None) -> int:
        """Return total number of movies (optionally filtered by genre)."""
        query = {"genres": genre} if genre else {}
        return await self.collection.count_documents(query)

    # ------------------------------------------------------------------
    # WRITE operations
    # ------------------------------------------------------------------

    async def insert_one(self, movie: MovieDocument) -> str:
        """
        Insert a single movie document. Returns the new document's _id as string.
        Will raise DuplicateKeyError if movie_id already exists (unique index).
        """
        doc = movie.model_dump(exclude={"id"}, by_alias=False)
        result = await self.collection.insert_one(doc)
        return str(result.inserted_id)

    async def bulk_insert(self, movies: List[MovieDocument]) -> int:
        """
        Insert a batch of movie documents efficiently.
        ordered=False: continue inserting even if one doc fails (e.g. duplicate).
        Returns count of successfully inserted documents.
        """
        if not movies:
            return 0
        docs = [m.model_dump(exclude={"id"}, by_alias=False) for m in movies]
        result = await self.collection.insert_many(docs, ordered=False)
        return len(result.inserted_ids)

    async def update_rating_stats(
        self, movie_id: int, new_rating: float
    ) -> Optional[MovieDocument]:
        """
        Incrementally update avg_rating and total_ratings when a new rating arrives.

        Instead of recalculating the average across all ratings in the DB,
        we use the running average formula:
            new_avg = (old_avg * old_count + new_rating) / (old_count + 1)

        MongoDB $inc and $set allow atomic field-level updates.

        Uses findOneAndUpdate with ReturnDocument.AFTER to return the updated doc.
        """
        # First, fetch current stats for the incremental calculation
        current = await self.find_by_movie_id(movie_id)
        if current is None:
            return None

        old_count = current.total_ratings
        old_avg = current.avg_rating
        new_count = old_count + 1
        new_avg = (old_avg * old_count + new_rating) / new_count

        updated_doc = await self.collection.find_one_and_update(
            {"movie_id": movie_id},
            {
                "$set": {"avg_rating": round(new_avg, 4)},
                "$inc": {"total_ratings": 1},
            },
            return_document=ReturnDocument.AFTER,
        )
        return MovieDocument(**updated_doc) if updated_doc else None
