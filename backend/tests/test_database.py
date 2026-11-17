import asyncio
import pytest
import pytest_asyncio
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

# --- Test configuration ---
MONGODB_URL = "mongodb://localhost:27017"
TEST_DB_NAME = "cinematch_db"


@pytest_asyncio.fixture
async def db() -> AsyncIOMotorDatabase:
    """
    Provide a fresh Motor database handle per test.
    Function scope ensures each test gets its own event loop binding.
    """
    client = AsyncIOMotorClient(MONGODB_URL, serverSelectionTimeoutMS=5000)
    database = client[TEST_DB_NAME]
    yield database
    client.close()


# ===========================================================================
# Test 1: MongoDB Connectivity
# ===========================================================================
@pytest.mark.asyncio
async def test_mongodb_connection(db):
    """Verify Motor can connect and ping the MongoDB server."""
    result = await db.command("ping")
    assert result.get("ok") == 1.0, "MongoDB ping failed"


# ===========================================================================
# Test 2: Collections Exist and Have Data
# ===========================================================================
@pytest.mark.asyncio
async def test_movies_collection_populated(db):
    """Verify movies collection has 1,682 documents (full MovieLens catalog)."""
    count = await db["movies"].count_documents({})
    assert count == 1682, f"Expected 1682 movies, got {count}"


@pytest.mark.asyncio
async def test_ratings_collection_populated(db):
    """Verify ratings collection has 100,000 documents."""
    count = await db["ratings"].count_documents({})
    assert count == 100_000, f"Expected 100000 ratings, got {count}"


# ===========================================================================
# Test 3: Indexes are Present
# ===========================================================================
@pytest.mark.asyncio
async def test_movie_unique_index(db):
    """Verify the unique index on movies.movie_id prevents duplicate inserts."""
    from pymongo.errors import DuplicateKeyError

    duplicate = {
        "movie_id": 1,          # movie_id=1 already exists from seeding
        "title":    "Toy Story (duplicate)",
        "genres":   ["Animation"],
        "avg_rating": 0.0,
        "total_ratings": 0,
        "popularity_score": 0.0,
    }
    with pytest.raises(DuplicateKeyError):
        await db["movies"].insert_one(duplicate)


@pytest.mark.asyncio
async def test_ratings_unique_compound_index(db):
    """Verify the unique (user_id, movie_id) compound index on ratings."""
    from pymongo.errors import DuplicateKeyError

    # Fetch an existing rating to try to duplicate
    existing = await db["ratings"].find_one({})
    assert existing is not None

    duplicate = {
        "user_id":  existing["user_id"],
        "movie_id": existing["movie_id"],
        "rating":   3.0,
    }
    with pytest.raises(DuplicateKeyError):
        await db["ratings"].insert_one(duplicate)


# ===========================================================================
# Test 4: MovieRepository
# ===========================================================================
@pytest.mark.asyncio
async def test_movie_repository_find_by_id(db):
    """MovieRepository.find_by_movie_id returns correct movie."""
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from backend.app.repositories.movie_repository import MovieRepository

    repo = MovieRepository(db)
    movie = await repo.find_by_movie_id(50)   # movie_id=50 is Star Wars

    assert movie is not None
    assert movie.movie_id == 50
    assert "Star Wars" in movie.title
    assert movie.total_ratings > 0
    assert movie.avg_rating > 0.0


@pytest.mark.asyncio
async def test_movie_repository_search(db):
    """MovieRepository full-text search returns relevant results."""
    from backend.app.repositories.movie_repository import MovieRepository

    repo = MovieRepository(db)
    results = await repo.search_by_title("star wars", limit=5)

    assert len(results) > 0
    # At least one result should contain "Star Wars"
    titles = [r.title for r in results]
    assert any("Star Wars" in t or "star" in t.lower() for t in titles)


@pytest.mark.asyncio
async def test_movie_repository_pagination(db):
    """MovieRepository.find_many respects skip and limit."""
    from backend.app.repositories.movie_repository import MovieRepository

    repo = MovieRepository(db)
    page1 = await repo.find_many(skip=0, limit=10)
    page2 = await repo.find_many(skip=10, limit=10)

    assert len(page1) == 10
    assert len(page2) == 10
    # Pages should not overlap
    ids1 = {m.movie_id for m in page1}
    ids2 = {m.movie_id for m in page2}
    assert ids1.isdisjoint(ids2), "Pagination pages overlap"


@pytest.mark.asyncio
async def test_movie_repository_genre_filter(db):
    """MovieRepository genre filter returns only matching movies."""
    from backend.app.repositories.movie_repository import MovieRepository

    repo = MovieRepository(db)
    sci_fi_movies = await repo.find_many(genre="Sci-Fi", limit=20)

    assert len(sci_fi_movies) > 0
    for movie in sci_fi_movies:
        assert "Sci-Fi" in movie.genres, f"Movie '{movie.title}' missing Sci-Fi genre"


# ===========================================================================
# Test 5: RatingRepository Aggregation
# ===========================================================================
@pytest.mark.asyncio
async def test_rating_repository_user_stats(db):
    """RatingRepository aggregation pipeline returns valid user statistics."""
    from backend.app.repositories.rating_repository import RatingRepository

    repo = RatingRepository(db)
    # user_id "1" has many ratings in the MovieLens dataset
    stats = await repo.get_user_rating_stats("1")

    assert "count" in stats
    assert "avg" in stats
    assert stats["count"] > 0
    assert 1.0 <= stats["avg"] <= 5.0
    assert 1.0 <= stats["min"] <= 5.0
    assert 1.0 <= stats["max"] <= 5.0


# ===========================================================================
# Test 6: Movie Stats Were Computed by Aggregation Pipeline
# ===========================================================================
@pytest.mark.asyncio
async def test_movie_stats_computed(db):
    """Star Wars (movie_id=50) should have avg_rating ≈ 4.35 and 583 ratings."""
    movie = await db["movies"].find_one({"movie_id": 50})
    assert movie is not None
    assert movie["total_ratings"] == 583
    assert 4.0 < movie["avg_rating"] < 4.6, f"Unexpected avg: {movie['avg_rating']}"
    assert movie["popularity_score"] > 0
