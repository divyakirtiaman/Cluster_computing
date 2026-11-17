"""
Watchlist Repository
--------------------
Handles all MongoDB operations for user watchlists.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

from backend.app.models.mongo_models import WatchlistDocument

logger = logging.getLogger("cinematch.watchlist")


class WatchlistRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db["watchlists"]

    async def add_movie(self, user_id: str, movie_id: int) -> bool:
        """
        Adds a movie to the user's watchlist.
        Returns True if added, False if already in watchlist.
        """
        doc = {
            "user_id": str(user_id),
            "movie_id": movie_id,
            "added_at": datetime.now(timezone.utc),
        }
        try:
            await self.collection.insert_one(doc)
            return True
        except DuplicateKeyError:
            return False

    async def remove_movie(self, user_id: str, movie_id: int) -> bool:
        """
        Removes a movie from the user's watchlist.
        Returns True if removed, False if not present.
        """
        result = await self.collection.delete_one({
            "user_id": str(user_id),
            "movie_id": movie_id
        })
        return result.deleted_count > 0

    async def get_user_watchlist(self, user_id: str) -> List[int]:
        """
        Returns list of movie IDs in the user's watchlist ordered by added date desc.
        """
        cursor = self.collection.find({"user_id": str(user_id)}).sort("added_at", -1)
        docs = await cursor.to_list(length=200)
        return [doc["movie_id"] for doc in docs]

    async def is_in_watchlist(self, user_id: str, movie_id: int) -> bool:
        """Checks if a movie is already in user's watchlist."""
        doc = await self.collection.find_one({
            "user_id": str(user_id),
            "movie_id": movie_id
        })
        return doc is not None
