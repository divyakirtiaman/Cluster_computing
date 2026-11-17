"""
CineMatch Database Seeder
--------------------------
Imports the MovieLens 100K dataset from processed Parquet files into MongoDB.

What this script does:
  1. Connects directly to MongoDB using Motor (runs its own asyncio event loop)
  2. Reads ml_engine/processed_data/movies.parquet (1,682 movies)
  3. Reads ml_engine/processed_data/ratings_train.parquet (79,901 ratings)
     + ml_engine/processed_data/ratings_test.parquet  (20,099 ratings)
  4. Bulk-inserts movies in batches of 100
  5. Bulk-inserts ratings in batches of 5,000
  6. Creates all indexes (idempotent — safe to run multiple times)

Usage:
  python scripts/seed_database.py              # fresh seed
  python scripts/seed_database.py --drop       # drop collections first, then seed

Why we seed from Parquet (not from raw .data files)?
  The Parquet files were already cleaned, deduplicated, and had genres
  converted from 19 binary columns to a single List[str] field (Phase 3).
  Re-using that work avoids re-implementing the transformation here.
"""

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import List

# Add project root to sys.path so we can import backend and ml_engine modules
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pyarrow.parquet as pq
from motor.motor_asyncio import AsyncIOMotorClient

# --- Paths ---
PROCESSED_DATA_DIR = PROJECT_ROOT / "ml_engine" / "data" / "processed"
MOVIES_PARQUET      = PROCESSED_DATA_DIR / "movies.parquet"
RATINGS_TRAIN_PARQUET = PROCESSED_DATA_DIR / "train_ratings.parquet"
RATINGS_TEST_PARQUET  = PROCESSED_DATA_DIR / "test_ratings.parquet"

# --- DB settings (must match backend/.env) ---
MONGODB_URL = "mongodb://localhost:27017"
DB_NAME     = "cinematch_db"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("seed")


# ---------------------------------------------------------------------------
# Genre extraction helper
# ---------------------------------------------------------------------------
# The movies Parquet has a column "genres" that was stored as an array<string>
# by the Phase 3 pipeline. PyArrow reads it as a Python list automatically.

def extract_release_year(title: str):
    """
    Extract the 4-digit year from MovieLens titles like "Star Wars (1977)".
    Returns None if no year is found.
    """
    import re
    match = re.search(r"\((\d{4})\)", title)
    return int(match.group(1)) if match else None


# ---------------------------------------------------------------------------
# Seed functions
# ---------------------------------------------------------------------------

async def seed_movies(db, batch_size: int = 100) -> int:
    """Read movies.parquet and insert into the 'movies' collection."""
    logger.info("Reading %s ...", MOVIES_PARQUET)
    table = pq.read_table(str(MOVIES_PARQUET))
    df = table.to_pydict()

    total = len(df["movie_id"])
    logger.info("Found %d movies to seed.", total)

    collection = db["movies"]
    inserted = 0
    skipped = 0

    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        batch = []
        for i in range(start, end):
            genres = df["genres"][i]
            # PyArrow may return genres as a pyarrow list — convert to plain list
            if hasattr(genres, "as_py"):
                genres = genres.as_py()
            if genres is None:
                genres = []

            title = str(df["title"][i])
            imdb_url = df["imdb_url"][i]
            if hasattr(imdb_url, "as_py"):
                imdb_url = imdb_url.as_py()

            movie_doc = {
                "movie_id":        int(df["movie_id"][i]),
                "title":           title,
                "genres":          genres,
                "release_year":    extract_release_year(title),
                "imdb_url":        str(imdb_url or ""),
                "avg_rating":      0.0,
                "total_ratings":   0,
                "popularity_score": 0.0,
            }
            batch.append(movie_doc)

        try:
            result = await collection.insert_many(batch, ordered=False)
            inserted += len(result.inserted_ids)
        except Exception as e:
            # DuplicateKeyError on re-seed — count as skipped
            skipped += len(batch)
            logger.debug("Batch skip (likely duplicates): %s", e)

        logger.info("Movies: %d / %d inserted ...", min(end, inserted + skipped), total)

    logger.info("Movies seeded: %d inserted, %d skipped (duplicates).", inserted, skipped)
    return inserted


async def seed_ratings(db, batch_size: int = 5000) -> int:
    """Read both ratings Parquet files and insert into the 'ratings' collection."""

    # Combine train + test sets (we want all 100K ratings in the DB)
    all_ratings = []
    for parquet_file in [RATINGS_TRAIN_PARQUET, RATINGS_TEST_PARQUET]:
        logger.info("Reading %s ...", parquet_file.name)
        table = pq.read_table(str(parquet_file))
        df = table.to_pydict()
        n = len(df["user_id"])
        for i in range(n):
            all_ratings.append({
                "user_id":  str(int(df["user_id"][i])),   # store as string for consistency
                "movie_id": int(df["movie_id"][i]),
                "rating":   float(df["rating"][i]),
                "rated_at": None,                          # historical data — no timestamp
            })

    total = len(all_ratings)
    logger.info("Total ratings to seed: %d", total)

    collection = db["ratings"]
    inserted = 0
    skipped = 0

    for start in range(0, total, batch_size):
        batch = all_ratings[start : start + batch_size]
        try:
            result = await collection.insert_many(batch, ordered=False)
            inserted += len(result.inserted_ids)
        except Exception as e:
            # Partial success — count inserted from the error object if available
            if hasattr(e, "details") and "nInserted" in e.details:
                inserted += e.details["nInserted"]
                skipped += len(batch) - e.details["nInserted"]
            else:
                skipped += len(batch)
            logger.debug("Rating batch error: %s", type(e).__name__)

        progress = min(start + batch_size, total)
        logger.info("Ratings: %d / %d ...", progress, total)

    logger.info("Ratings seeded: %d inserted, %d skipped.", inserted, skipped)
    return inserted


async def update_movie_stats(db) -> None:
    """
    After all ratings are inserted, run an aggregation pipeline to compute
    per-movie avg_rating and total_ratings, then update each movie document.

    Aggregation pipeline stages:
      $group  → group rating documents by movie_id, compute avg and count
      $merge  → write results back into the 'movies' collection

    This is more efficient than updating one movie at a time (1,682 updates
    vs. one aggregation pass over 100K documents).
    """
    logger.info("Computing movie rating statistics via aggregation pipeline ...")
    pipeline = [
        {
            "$group": {
                "_id":           "$movie_id",
                "avg_rating":    {"$avg": "$rating"},
                "total_ratings": {"$sum": 1},
            }
        },
        {
            # Rename _id → movie_id and compute popularity_score
            "$project": {
                "_id":           0,                 # suppress _id from $group output
                "movie_id":      "$_id",
                "avg_rating":    {"$round": ["$avg_rating", 4]},
                "total_ratings": 1,
                "popularity_score": {
                    "$multiply": [
                        {"$round": ["$avg_rating", 4]},
                        {"$ln": {"$add": ["$total_ratings", 1]}}
                    ]
                }
            }
        },
        {
            "$merge": {
                "into":           "movies",
                "on":             "movie_id",
                # whenMatched pipeline: update only the stats fields, leave _id untouched
                "whenMatched":    [
                    {"$set": {
                        "avg_rating":      "$$new.avg_rating",
                        "total_ratings":   "$$new.total_ratings",
                        "popularity_score": "$$new.popularity_score",
                    }}
                ],
                "whenNotMatched": "discard",
            }
        }
    ]
    await db["ratings"].aggregate(pipeline).to_list(length=None)
    logger.info("Movie stats updated (avg_rating, total_ratings, popularity_score).")


async def run_seed(drop_first: bool = False) -> None:
    """Main seeding orchestration."""
    client = AsyncIOMotorClient(MONGODB_URL, serverSelectionTimeoutMS=5000)
    db = client[DB_NAME]

    # Verify connectivity
    await db.command("ping")
    logger.info("MongoDB connected: %s / %s", MONGODB_URL, DB_NAME)

    if drop_first:
        logger.warning("--drop flag set. Dropping movies and ratings collections ...")
        await db["movies"].drop()
        await db["ratings"].drop()
        logger.info("Collections dropped.")

    # Create indexes before inserting (more efficient)
    from pymongo import ASCENDING, TEXT
    await db["movies"].create_index([("movie_id", ASCENDING)], unique=True, name="movies_movie_id_unique")
    await db["movies"].create_index([("title", TEXT)], name="movies_title_text")
    await db["ratings"].create_index(
        [("user_id", ASCENDING), ("movie_id", ASCENDING)],
        unique=True, name="ratings_user_movie_unique"
    )

    t0 = time.perf_counter()

    movies_inserted = await seed_movies(db)
    ratings_inserted = await seed_ratings(db)
    await update_movie_stats(db)

    elapsed = time.perf_counter() - t0
    client.close()

    print("\n" + "=" * 55)
    print("  CineMatch Database Seed — COMPLETE")
    print("=" * 55)
    print(f"  Movies inserted  : {movies_inserted:>7,}")
    print(f"  Ratings inserted : {ratings_inserted:>7,}")
    print(f"  Total time       : {elapsed:.1f}s")
    print("=" * 55)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed CineMatch MongoDB database.")
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop existing movies and ratings collections before seeding.",
    )
    args = parser.parse_args()
    asyncio.run(run_seed(drop_first=args.drop))
