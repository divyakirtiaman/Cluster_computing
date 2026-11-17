"""
Database & Cache Connection Managers
--------------------------------------
Motor (async MongoDB driver) connection with connection pooling.
Motor wraps PyMongo in asyncio-compatible coroutines so FastAPI's event
loop is never blocked during database I/O.

Connection Lifecycle (managed by FastAPI lifespan):
  Startup  → connect_to_mongo()   creates the Motor client + ensures indexes
  Shutdown → close_mongo_connection()  flushes the connection pool

Usage in route handlers (via FastAPI dependency injection):
  async def my_route(db: AsyncIOMotorDatabase = Depends(get_db)):
      user = await db["users"].find_one({"email": email})
"""

import logging
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, TEXT

from backend.app.core.config import settings

logger = logging.getLogger("cinematch.db")

# ---------------------------------------------------------------------------
# Module-level singletons — set by connect_to_mongo(), cleared by close_mongo
# ---------------------------------------------------------------------------
_mongo_client: Optional[AsyncIOMotorClient] = None
_database: Optional[AsyncIOMotorDatabase] = None
_is_connected: bool = False


# ---------------------------------------------------------------------------
# Index Definitions
# ---------------------------------------------------------------------------
# Indexes are created idempotently (create_index is a no-op if already exists).
# Each tuple is (collection_name, index_spec, options).
# index_spec follows pymongo format: list of (field, direction) tuples.
#
# Why these specific indexes?
#   - ratings (user_id, movie_id) UNIQUE compound: prevents duplicate ratings,
#     and covers the most common lookup pattern "fetch all ratings by user X".
#   - movies title TEXT: enables full-text search with $text operator,
#     MongoDB tokenizes & stems the title automatically.
#   - watchlists (user_id, movie_id) UNIQUE compound: same rationale as ratings.
#   - recommendation_history user_id: fast lookup of a user's rec history.
# ---------------------------------------------------------------------------
INDEX_DEFINITIONS = [
    # collection         index_spec                                   options
    ("users",            [("email", ASCENDING)],                      {"unique": True, "name": "users_email_unique"}),
    ("users",            [("username", ASCENDING)],                   {"unique": True, "name": "users_username_unique"}),
    ("movies",           [("movie_id", ASCENDING)],                   {"unique": True, "name": "movies_movie_id_unique"}),
    ("movies",           [("title", TEXT)],                           {"name": "movies_title_text"}),
    ("ratings",          [("user_id", ASCENDING), ("movie_id", ASCENDING)], {"unique": True, "name": "ratings_user_movie_unique"}),
    ("ratings",          [("user_id", ASCENDING)],                    {"name": "ratings_by_user"}),
    ("ratings",          [("movie_id", ASCENDING)],                   {"name": "ratings_by_movie"}),
    ("watchlists",       [("user_id", ASCENDING), ("movie_id", ASCENDING)], {"unique": True, "name": "watchlist_user_movie_unique"}),
    ("watchlists",       [("user_id", ASCENDING)],                    {"name": "watchlist_by_user"}),
    ("recommendation_history", [("user_id", ASCENDING)],             {"name": "recs_by_user"}),
    ("recommendation_history", [("generated_at", ASCENDING)],        {"name": "recs_by_time"}),
]


def _is_mongo_reachable(url: str) -> bool:
    """Fast non-blocking socket probe to verify MongoDB port is open before initializing Motor."""
    import socket
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 27017
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.2)
            return s.connect_ex((host, port)) == 0
    except Exception:
        return False


async def connect_to_mongo() -> None:
    """
    Create the Motor client and wire up the module-level singletons.
    Probes socket first to avoid thread pool blocking if MongoDB is offline.
    """
    global _mongo_client, _database, _is_connected

    logger.info("Connecting to MongoDB at %s ...", settings.MONGODB_URL)

    if not _is_mongo_reachable(settings.MONGODB_URL):
        logger.warning(
            "MongoDB server unreachable at %s. Running in fallback mode.",
            settings.MONGODB_URL
        )
        _is_connected = False
        return

    try:
        _mongo_client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            maxPoolSize=50,
            minPoolSize=0,
            serverSelectionTimeoutMS=1000,
        )
        _database = _mongo_client[settings.MONGODB_DB_NAME]
        await _database.command("ping")
        _is_connected = True
        logger.info("MongoDB connected — database: '%s'", settings.MONGODB_DB_NAME)
        await _create_indexes()
    except Exception as exc:
        _is_connected = False
        logger.warning("MongoDB init error (%s). Running in fallback mode.", exc)


async def _create_indexes() -> None:
    """Create all required indexes. Called once during startup."""
    logger.info("Ensuring MongoDB indexes ...")
    for collection_name, index_spec, options in INDEX_DEFINITIONS:
        collection = _database[collection_name]
        try:
            await collection.create_index(index_spec, **options)
            logger.debug("Index '%s' on '%s' — OK", options.get("name"), collection_name)
        except Exception as exc:
            # Log and continue — a duplicate index name on a different spec
            # will raise, but we don't want that to crash the entire app.
            logger.warning("Index creation warning on '%s': %s", collection_name, exc)
    logger.info("All MongoDB indexes verified.")


async def close_mongo_connection() -> None:
    """
    Cleanly shut down the Motor connection pool.
    Called by FastAPI's lifespan shutdown handler.
    """
    global _mongo_client, _database, _is_connected
    if _mongo_client is not None:
        _mongo_client.close()
        _mongo_client = None
        _database = None
        _is_connected = False
        logger.info("MongoDB connection pool closed.")


def is_mongo_connected() -> bool:
    """Return whether MongoDB is actively connected and reachable."""
    return _is_connected


def get_database() -> AsyncIOMotorDatabase:
    """
    Return the active Motor database handle.
    Raises RuntimeError if called before connect_to_mongo().

    Designed for use as a FastAPI dependency:
        async def route(db = Depends(get_database)):
            ...
    """
    if _database is None:
        raise RuntimeError(
            "MongoDB not connected. "
            "Ensure connect_to_mongo() ran during app startup."
        )
    return _database


# Convenience alias used throughout the app
get_db = get_database
