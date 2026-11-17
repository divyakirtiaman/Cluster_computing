"""
High-Performance Recommendation & Catalog Service Layer
Loads ML factor models and precomputed Parquet artifacts via PyArrow for sub-millisecond
API responses, supporting real-time dot-product inference and similarity lookups.
"""

import time
from pathlib import Path
from typing import Dict, List, Optional
import pyarrow.parquet as pq

from backend.app.schemas.movie import MovieResponse, MovieSummary
from backend.app.schemas.recommendation import RecommendationResponse, SimilarMoviesResponse
from backend.app.core.cache import (
    cache_service,
    get_cache_key_user_recs,
    get_cache_key_similar_movies,
    get_cache_key_movie,
    get_cache_key_catalog,
    PREFIX_GENRES,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
PROCESSED_DATA_DIR = PROJECT_ROOT / "ml_engine" / "data" / "processed"

# ---------------------------------------------------------------------------
# Diverse poster pool — 24 distinct Unsplash cinema / genre images.
# Each movie is assigned deterministically via  movie_id % len(POSTER_POOL)
# so the same movie always gets the same poster across restarts.
# ---------------------------------------------------------------------------
POSTER_POOL = [
    "https://images.unsplash.com/photo-1536440136628-849c177e76a1?w=500&q=80",  # 0  dark cinema
    "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=500&q=80",  # 1  cinema seats
    "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=500&q=80",  # 2  starry sky
    "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=500&q=80",  # 3  space planet
    "https://images.unsplash.com/photo-1574375927938-d5a98e8ffe85?w=500&q=80",  # 4  drama stage
    "https://images.unsplash.com/photo-1509198397868-475647b2a1e5?w=500&q=80",  # 5  thriller dark
    "https://images.unsplash.com/photo-1478760329108-5c3ed9d495a0?w=500&q=80",  # 6  action fire
    "https://images.unsplash.com/photo-1500462918059-b1a0cb512f1d?w=500&q=80",  # 7  animation colour
    "https://images.unsplash.com/photo-1517604931442-7e0c8ed2963c?w=500&q=80",  # 8  classic film strip
    "https://images.unsplash.com/photo-1512070679279-8988d32161be?w=500&q=80",  # 9  adventure jungle
    "https://images.unsplash.com/photo-1440404653325-ab127d49abc1?w=500&q=80",  # 10 comedy laughing
    "https://images.unsplash.com/photo-1593642632559-0c6d3fc62b89?w=500&q=80",  # 11 sci-fi neon
    "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=500&q=80",  # 12 romance sunset
    "https://images.unsplash.com/photo-1525373698358-041e3a460346?w=500&q=80",  # 13 western desert
    "https://images.unsplash.com/photo-1495147466023-ac5c588e2e94?w=500&q=80",  # 14 horror shadow
    "https://images.unsplash.com/photo-1467043237213-65f2da53396f?w=500&q=80",  # 15 musical stage
    "https://images.unsplash.com/photo-1626814026160-2237a95fc5a0?w=500&q=80",  # 16 war dramatic
    "https://images.unsplash.com/photo-1543852786-1cf6624b9987?w=500&q=80",     # 17 documentary lens
    "https://images.unsplash.com/photo-1560109947-543149787f8f?w=500&q=80",     # 18 mystery fog
    "https://images.unsplash.com/photo-1555680202-c86f0e12f086?w=500&q=80",     # 19 crime night
    "https://images.unsplash.com/photo-1546768292-fb12f6c92568?w=500&q=80",     # 20 fantasy castle
    "https://images.unsplash.com/photo-1504384308090-c894fdcc538d?w=500&q=80",  # 21 tech cyber
    "https://images.unsplash.com/photo-1485846234645-a62644f84728?w=500&q=80",  # 22 film camera
    "https://images.unsplash.com/photo-1524712245354-2c4e5e7121c0?w=500&q=80",  # 23 dramatic portrait
]


def _poster_for(movie_id: int) -> str:
    """Return a deterministic poster URL for a given movie_id."""
    return POSTER_POOL[movie_id % len(POSTER_POOL)]


class RecommendationService:
    def __init__(self):
        self._movies_catalog: Dict[int, dict] = {}
        self._top_recs_by_user: Dict[int, list] = {}
        self._similar_by_movie: Dict[int, list] = {}
        self._user_factors: Dict[int, list] = {}
        self._item_factors: Dict[int, list] = {}
        self._all_genres: List[str] = []
        self._is_loaded = False
        self._load_datasets()

    def _load_datasets(self):
        """Loads clean Parquet datasets into high-speed memory lookups."""
        start = time.perf_counter()

        # 1. Load Movies Catalog
        movies_path = PROCESSED_DATA_DIR / "movies.parquet"
        if movies_path.exists():
            table = pq.read_table(str(movies_path))
            pydict = table.to_pydict()
            genres_set = set()
            for idx in range(len(pydict["movie_id"])):
                m_id = pydict["movie_id"][idx]
                genres = list(pydict["genres"][idx])
                for g in genres:
                    genres_set.add(g)
                self._movies_catalog[m_id] = {
                    "movie_id": m_id,
                    "title": pydict["title"][idx],
                    "release_date": pydict["release_date"][idx],
                    "imdb_url": pydict["imdb_url"][idx],
                    "genres": genres,
                    "poster_url": _poster_for(m_id)
                }
            self._all_genres = sorted(list(genres_set))

        # 2. Load Precomputed Top Recommendations
        recs_path = PROCESSED_DATA_DIR / "top_recommendations.parquet"
        if recs_path.exists():
            table = pq.read_table(str(recs_path))
            pydict = table.to_pydict()
            for idx in range(len(pydict["user_id"])):
                u_id = pydict["user_id"][idx]
                if u_id not in self._top_recs_by_user:
                    self._top_recs_by_user[u_id] = []
                self._top_recs_by_user[u_id].append({
                    "movie_id": pydict["movie_id"][idx],
                    "title": pydict["title"][idx],
                    "genres": list(pydict["genres"][idx]),
                    "predicted_rating": pydict["predicted_rating"][idx],
                    "poster_url": _poster_for(pydict["movie_id"][idx])
                })

        # 3. Load Precomputed Similar Movies
        sim_path = PROCESSED_DATA_DIR / "similar_movies.parquet"
        if sim_path.exists():
            table = pq.read_table(str(sim_path))
            pydict = table.to_pydict()
            for idx in range(len(pydict["source_movie_id"])):
                s_id = pydict["source_movie_id"][idx]
                if s_id not in self._similar_by_movie:
                    self._similar_by_movie[s_id] = []
                self._similar_by_movie[s_id].append({
                    "movie_id": pydict["similar_movie_id"][idx],
                    "title": pydict["similar_title"][idx],
                    "genres": list(pydict["similar_genres"][idx]),
                    "similarity_score": round(float(pydict["similarity_score"][idx]), 4),
                    "poster_url": _poster_for(pydict["similar_movie_id"][idx])
                })

        # 4. Load User & Item Factors for Real-time Dot-Product
        user_fac_path = PROCESSED_DATA_DIR / "user_factors.parquet"
        if user_fac_path.exists():
            table = pq.read_table(str(user_fac_path))
            pydict = table.to_pydict()
            for idx in range(len(pydict["id"])):
                self._user_factors[pydict["id"][idx]] = list(pydict["features"][idx])

        item_fac_path = PROCESSED_DATA_DIR / "item_factors.parquet"
        if item_fac_path.exists():
            table = pq.read_table(str(item_fac_path))
            pydict = table.to_pydict()
            for idx in range(len(pydict["id"])):
                self._item_factors[pydict["id"][idx]] = list(pydict["features"][idx])

        elapsed_ms = (time.perf_counter() - start) * 1000
        self._is_loaded = True
        print(f"[RecSysService] Loaded {len(self._movies_catalog):,} movies, {len(self._top_recs_by_user):,} user recs, and factor matrices into RAM in {elapsed_ms:.1f}ms.")

    async def get_user_recommendations(self, user_id: int, top_n: int = 10) -> RecommendationResponse:
        """Returns precomputed ALS top-N recommendations for a user with Redis caching."""
        start = time.perf_counter()

        cache_key = get_cache_key_user_recs(user_id, top_n)
        cached_data = await cache_service.get_json(cache_key)
        if cached_data:
            cached_data["execution_time_ms"] = round((time.perf_counter() - start) * 1000, 2)
            cached_data["explanation"] = "Served in microseconds from Redis cache"
            return RecommendationResponse(**cached_data)

        recs_data = self._top_recs_by_user.get(user_id)
        if not recs_data:
            # Fallback to general popular movies if user_id is unseen (Cold Start)
            recs_data = list(self._movies_catalog.values())[:top_n]

        recommendations = [
            MovieSummary(
                movie_id=m["movie_id"],
                title=m["title"],
                genres=m.get("genres", []),
                poster_url=m.get("poster_url"),
                predicted_rating=m.get("predicted_rating")
            )
            for m in recs_data[:top_n]
        ]

        elapsed_ms = (time.perf_counter() - start) * 1000
        response = RecommendationResponse(
            user_id=user_id,
            algorithm="ALS-MatrixFactorization",
            recommendations=recommendations,
            execution_time_ms=round(elapsed_ms, 2),
            explanation="Personalized via Spark MLlib ALS latent factor decomposition"
        )

        # Store in Redis cache
        await cache_service.set_json(cache_key, response.model_dump())
        return response

    async def get_similar_movies(self, movie_id: int, top_n: int = 5) -> SimilarMoviesResponse:
        """Returns the top-N semantically similar movies with Redis caching."""
        cache_key = get_cache_key_similar_movies(movie_id, top_n)
        cached_data = await cache_service.get_json(cache_key)
        if cached_data:
            return SimilarMoviesResponse(**cached_data)

        sim_data = self._similar_by_movie.get(movie_id, [])
        similar_movies = [
            MovieSummary(
                movie_id=m["movie_id"],
                title=m["title"],
                genres=m.get("genres", []),
                poster_url=m.get("poster_url"),
                predicted_rating=m.get("similarity_score")
            )
            for m in sim_data[:top_n]
        ]
        response = SimilarMoviesResponse(
            source_movie_id=movie_id,
            similar_movies=similar_movies
        )
        await cache_service.set_json(cache_key, response.model_dump())
        return response

    async def predict_rating_realtime(self, user_id: int, movie_id: int) -> Optional[float]:
        """
        Computes real-time dot product prediction: r_hat = u_u^T * v_i
        Executes in microseconds directly from in-memory factor arrays!
        """
        u_vec = self._user_factors.get(user_id)
        v_vec = self._item_factors.get(movie_id)

        if not u_vec or not v_vec:
            return None

        dot_product = sum(u * v for u, v in zip(u_vec, v_vec))
        # Clamp between 1.0 and 5.0
        predicted = max(1.0, min(5.0, dot_product))
        return round(predicted, 2)

    async def list_movies(self, genre: Optional[str] = None, search: Optional[str] = None, limit: int = 20) -> List[MovieResponse]:
        """Searches and filters movies from the loaded catalog."""
        results = list(self._movies_catalog.values())
        if genre and genre.lower() != "all":
            results = [m for m in results if any(genre.lower() == g.lower() for g in m["genres"])]
        if search:
            query = search.lower()
            results = [m for m in results if query in m["title"].lower()]

        return [MovieResponse(**m) for m in results[:limit]]

    async def get_movie_by_id(self, movie_id: int) -> Optional[MovieResponse]:
        """Returns details for a single movie ID with Redis caching."""
        cache_key = get_cache_key_movie(movie_id)
        cached = await cache_service.get_json(cache_key)
        if cached:
            return MovieResponse(**cached)

        data = self._movies_catalog.get(movie_id)
        if not data:
            return None

        response = MovieResponse(**data)
        await cache_service.set_json(cache_key, response.model_dump())
        return response

    def get_genres(self) -> List[str]:
        return self._all_genres


recsys_service = RecommendationService()
