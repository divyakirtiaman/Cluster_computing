"""
CineMatch High-Performance Redis Caching Layer
-----------------------------------------------
Provides asynchronous Redis caching for:
  - Top-N personalized recommendations (per user)
  - Similar movies (per movie)
  - Catalog query results & genre lists
  - Real-time rating cache invalidation

Features:
  - Asynchronous non-blocking connection pool via redis.asyncio
  - Automatic JSON serialization and deserialization
  - Resilient In-Memory fallback cache when Redis server is offline
  - Standardized namespace key patterns
  - Atomic pattern invalidation via SCAN + UNLINK/DEL
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union
import redis.asyncio as aioredis
from redis.asyncio.connection import ConnectionPool
from redis.exceptions import RedisError

from backend.app.core.config import settings

logger = logging.getLogger("cinematch.cache")

# Namespace key prefixes
PREFIX_USER_RECS = "cinematch:recs:user"
PREFIX_SIMILAR_MOVIES = "cinematch:similar:movie"
PREFIX_MOVIE = "cinematch:movie"
PREFIX_CATALOG = "cinematch:catalog"
PREFIX_GENRES = "cinematch:genres"

_redis_pool: Optional[ConnectionPool] = None
_redis_client: Optional[aioredis.Redis] = None
_is_connected: bool = False

# High-performance in-memory fallback cache (used if Redis is offline/testing)
_memory_cache: Dict[str, Any] = {}


def get_cache_key_user_recs(user_id: Union[int, str], limit: int) -> str:
    """Standardized key for user recommendations."""
    return f"{PREFIX_USER_RECS}:{user_id}:{limit}"


def get_cache_key_similar_movies(movie_id: int, limit: int) -> str:
    """Standardized key for movie similarities."""
    return f"{PREFIX_SIMILAR_MOVIES}:{movie_id}:{limit}"


def get_cache_key_movie(movie_id: int) -> str:
    """Standardized key for a movie detail."""
    return f"{PREFIX_MOVIE}:{movie_id}"


def get_cache_key_catalog(genre: Optional[str], search: Optional[str], limit: int) -> str:
    """Standardized key for catalog listings."""
    g = genre or "all"
    s = (search or "none").strip().lower()
    return f"{PREFIX_CATALOG}:{g}:{s}:{limit}"


def _is_redis_reachable(url: str) -> bool:
    """Fast non-blocking socket probe to verify Redis port is open before connecting."""
    import socket
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 6379
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.2)
            return s.connect_ex((host, port)) == 0
    except Exception:
        return False


class CacheService:
    """
    Asynchronous caching engine with transparent Redis and fallback handling.
    """

    def __init__(self):
        self.default_ttl = settings.REDIS_CACHE_TTL_SECONDS

    async def connect(self) -> bool:
        """
        Initializes the async Redis connection pool.
        Attempts ping; if unreachable, gracefully marks Redis unavailable.
        """
        global _redis_pool, _redis_client, _is_connected
        if not _is_redis_reachable(settings.REDIS_URL):
            logger.info("Redis host unreachable at %s. Operating in in-memory fallback mode.", settings.REDIS_URL)
            _is_connected = False
            return False

        try:
            logger.info("Initializing Redis connection to %s ...", settings.REDIS_URL)
            _redis_pool = ConnectionPool.from_url(
                settings.REDIS_URL,
                max_connections=20,
                decode_responses=True,
                socket_timeout=1.0,
                socket_connect_timeout=1.0,
            )
            _redis_client = aioredis.Redis(connection_pool=_redis_pool)
            await _redis_client.ping()
            _is_connected = True
            logger.info("Redis cache connected successfully. Active URL: %s", settings.REDIS_URL)
            return True
        except Exception as exc:
            _is_connected = False
            logger.warning(
                "Redis connection failed (%s). CacheService operating in in-memory fallback mode.",
                exc
            )
            return False

    async def close(self) -> None:
        """Closes the Redis client and connection pool cleanly."""
        global _redis_pool, _redis_client, _is_connected
        if _redis_client:
            try:
                await _redis_client.aclose()
            except Exception:
                pass
            _redis_client = None
        if _redis_pool:
            try:
                await _redis_pool.disconnect()
            except Exception:
                pass
            _redis_pool = None
        _is_connected = False
        _memory_cache.clear()
        logger.info("Redis cache pool closed.")

    @property
    def is_connected(self) -> bool:
        """Returns True if live Redis connection is active."""
        return _is_connected

    async def get_json(self, key: str) -> Optional[Any]:
        """
        Retrieves a cached JSON-serialized object by key.
        Returns None if cache misses, key expired, or on error.
        """
        if _is_connected and _redis_client:
            try:
                val = await _redis_client.get(key)
                if val is not None:
                    return json.loads(val)
                return None
            except RedisError as err:
                logger.debug("Redis GET error for key %s: %s", key, err)
                # Fall through to memory cache

        return _memory_cache.get(key)

    async def set_json(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Serializes value to JSON and stores it with an expiration TTL (seconds).
        """
        expire_time = ttl if ttl is not None else self.default_ttl
        serialized = json.dumps(value)

        stored = False
        if _is_connected and _redis_client:
            try:
                await _redis_client.set(key, serialized, ex=expire_time)
                stored = True
            except RedisError as err:
                logger.debug("Redis SET error for key %s: %s", key, err)

        # Mirror/fallback to memory cache
        _memory_cache[key] = value
        return stored or True

    async def delete(self, key: str) -> bool:
        """Deletes a single key from cache."""
        deleted = False
        if _is_connected and _redis_client:
            try:
                await _redis_client.delete(key)
                deleted = True
            except RedisError as err:
                logger.debug("Redis DEL error for key %s: %s", key, err)

        _memory_cache.pop(key, None)
        return deleted

    async def delete_pattern(self, pattern: str) -> int:
        """
        Scans and deletes all keys matching the given glob pattern.
        E.g. 'cinematch:recs:user:1:*'
        """
        count = 0
        if _is_connected and _redis_client:
            try:
                keys: List[str] = []
                async for key in _redis_client.scan_iter(match=pattern, count=100):
                    keys.append(key)
                if keys:
                    count = await _redis_client.delete(*keys)
            except RedisError as err:
                logger.debug("Redis SCAN/DEL error for pattern %s: %s", pattern, err)

        # In-memory pattern cleanup
        import fnmatch
        keys_to_del = [k for k in _memory_cache if fnmatch.fnmatch(k, pattern)]
        for k in keys_to_del:
            _memory_cache.pop(k, None)
        count = max(count, len(keys_to_del))

        return count

    async def invalidate_user_recommendations(self, user_id: Union[int, str]) -> int:
        """
        Invalidates all cached recommendation variants for a given user.
        Crucial when the user submits a new rating or alters genre preferences.
        """
        pattern = f"{PREFIX_USER_RECS}:{user_id}:*"
        count = await self.delete_pattern(pattern)
        logger.info("Invalidated %d cached recommendation entries for user %s", count, user_id)
        return count

    async def invalidate_movie_cache(self, movie_id: int) -> int:
        """
        Invalidates cached metadata and similar movie entries for a movie.
        """
        count = 0
        count += 1 if await self.delete(get_cache_key_movie(movie_id)) else 0
        count += await self.delete_pattern(f"{PREFIX_SIMILAR_MOVIES}:{movie_id}:*")
        logger.info("Invalidated %d cache entries for movie %s", count, movie_id)
        return count

    async def clear_all(self) -> None:
        """Clears CineMatch keys from cache."""
        if _is_connected and _redis_client:
            try:
                await self.delete_pattern("cinematch:*")
            except Exception:
                pass
        _memory_cache.clear()


cache_service = CacheService()
