"""
Unit and Integration Test Suite for CineMatch Redis Caching Layer
Tests JSON serialization, namespace keys, pattern deletion,
user recommendation invalidation, and fallback behaviors.
"""

import pytest
import pytest_asyncio
from backend.app.core.cache import (
    cache_service,
    get_cache_key_user_recs,
    get_cache_key_similar_movies,
    get_cache_key_movie,
    get_cache_key_catalog
)


@pytest.mark.asyncio
async def test_cache_set_and_get():
    """Verify storing and retrieving JSON objects."""
    key = "cinematch:test:sample_obj"
    sample_data = {"user_id": 1, "movie_id": 50, "rating": 4.5, "tags": ["sci-fi", "space"]}

    await cache_service.set_json(key, sample_data, ttl=60)
    retrieved = await cache_service.get_json(key)

    assert retrieved is not None
    assert retrieved["user_id"] == 1
    assert retrieved["movie_id"] == 50
    assert retrieved["tags"] == ["sci-fi", "space"]

    # Delete
    await cache_service.delete(key)
    assert await cache_service.get_json(key) is None


@pytest.mark.asyncio
async def test_user_recommendations_invalidation():
    """Verify invalidating a user's recommendations removes all limit variants."""
    user_id = 99
    key_top5 = get_cache_key_user_recs(user_id, 5)
    key_top10 = get_cache_key_user_recs(user_id, 10)
    key_other = get_cache_key_user_recs(100, 10)

    await cache_service.set_json(key_top5, [{"movie_id": 1}], ttl=300)
    await cache_service.set_json(key_top10, [{"movie_id": 1}, {"movie_id": 2}], ttl=300)
    await cache_service.set_json(key_other, [{"movie_id": 50}], ttl=300)

    assert await cache_service.get_json(key_top5) is not None
    assert await cache_service.get_json(key_top10) is not None
    assert await cache_service.get_json(key_other) is not None

    # Invalidate user 99
    deleted_count = await cache_service.invalidate_user_recommendations(user_id)
    assert deleted_count >= 2

    assert await cache_service.get_json(key_top5) is None
    assert await cache_service.get_json(key_top10) is None
    # User 100 cache must remain intact
    assert await cache_service.get_json(key_other) is not None


@pytest.mark.asyncio
async def test_movie_cache_invalidation():
    """Verify invalidating movie metadata and similarity keys."""
    movie_id = 77
    detail_key = get_cache_key_movie(movie_id)
    sim_key = get_cache_key_similar_movies(movie_id, 5)

    await cache_service.set_json(detail_key, {"title": "Test Title"}, ttl=300)
    await cache_service.set_json(sim_key, [{"similar_id": 78}], ttl=300)

    count = await cache_service.invalidate_movie_cache(movie_id)
    assert count >= 1
    assert await cache_service.get_json(detail_key) is None
    assert await cache_service.get_json(sim_key) is None
