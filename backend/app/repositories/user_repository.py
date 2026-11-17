"""
User Repository
----------------
All MongoDB operations for the 'users' collection.

Responsibilities:
  - Create new user accounts (with hashed password, never plain text)
  - Look up users by email or username (for login/uniqueness checks)
  - Update user preferences (genre preferences, settings)
  - Increment the denormalized 'total_ratings' counter

Security note:
  This repository stores and retrieves hashed_password fields.
  Plain-text passwords NEVER enter this module — that responsibility
  belongs to backend/app/core/security.py (bcrypt hash/verify).
"""

from typing import List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from backend.app.models.mongo_models import UserDocument


class UserRepository:
    """
    Encapsulates all MongoDB operations for the users collection.
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db["users"]

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    async def find_by_email(self, email: str) -> Optional[UserDocument]:
        """
        Look up a user by email address.
        Uses the unique index on 'email' — O(log n).
        Returns None if not found.
        """
        doc = await self.collection.find_one({"email": email.lower()})
        return UserDocument(**doc) if doc else None

    async def find_by_username(self, username: str) -> Optional[UserDocument]:
        """Look up a user by username. Used for uniqueness checks on registration."""
        doc = await self.collection.find_one({"username": username})
        return UserDocument(**doc) if doc else None

    async def find_by_id(self, user_id: str) -> Optional[UserDocument]:
        """
        Look up a user by their MongoDB _id (as string).
        bson.ObjectId converts the string back to the binary ObjectId type
        for the query — MongoDB requires _id queries to use the ObjectId type.
        """
        from bson import ObjectId
        try:
            oid = ObjectId(user_id)
        except Exception:
            return None     # invalid ObjectId string → not found
        doc = await self.collection.find_one({"_id": oid})
        return UserDocument(**doc) if doc else None

    # ------------------------------------------------------------------
    # WRITE
    # ------------------------------------------------------------------

    async def create_user(self, user: UserDocument) -> str:
        """
        Insert a new user document. Returns the new _id as a string.
        Normalizes email to lowercase before storing.
        Raises DuplicateKeyError if email or username already exists.
        """
        doc = user.model_dump(exclude={"id"}, by_alias=False)
        doc["email"] = doc["email"].lower()     # enforce lowercase email storage
        result = await self.collection.insert_one(doc)
        return str(result.inserted_id)

    async def update_preferred_genres(
        self, user_id: str, genres: List[str]
    ) -> Optional[UserDocument]:
        """
        Replace the user's preferred_genres array.
        Returns the updated UserDocument.
        """
        from bson import ObjectId
        updated = await self.collection.find_one_and_update(
            {"_id": ObjectId(user_id)},
            {"$set": {"preferred_genres": genres}},
            return_document=ReturnDocument.AFTER,
        )
        return UserDocument(**updated) if updated else None

    async def increment_rating_count(self, user_id: str) -> None:
        """
        Atomically increment the denormalized total_ratings counter.
        Called every time a user submits a new rating.
        $inc is atomic in MongoDB — safe under concurrent requests.
        """
        from bson import ObjectId
        await self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$inc": {"total_ratings": 1}},
        )
