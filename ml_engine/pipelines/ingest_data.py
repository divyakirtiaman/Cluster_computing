"""
Data Ingestion, Cleaning & Preprocessing Pipeline
Loads raw MovieLens 100K files into typed PySpark DataFrames, applies rigorous cleaning
and validation, extracts genre arrays, and exports optimized Parquet train/test partitions.
"""

import sys
from pathlib import Path
from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import ArrayType, StringType

from ml_engine.config import (
    RATINGS_FILE,
    MOVIES_FILE,
    USERS_FILE,
    PROCESSED_DATA_DIR
)
from ml_engine.schemas import RATINGS_SCHEMA, MOVIES_SCHEMA, USERS_SCHEMA, GENRE_COLUMNS
from ml_engine.utils.spark_session import get_spark_session


def load_raw_ratings(spark) -> DataFrame:
    """Loads u.data with tab delimiter and explicit schema."""
    return (
        spark.read
        .format("csv")
        .option("delimiter", "\t")
        .schema(RATINGS_SCHEMA)
        .load(str(RATINGS_FILE))
    )


def load_raw_movies(spark) -> DataFrame:
    """Loads u.item with pipe delimiter and latin-1 encoding."""
    return (
        spark.read
        .format("csv")
        .option("delimiter", "|")
        .option("encoding", "ISO-8859-1")
        .schema(MOVIES_SCHEMA)
        .load(str(MOVIES_FILE))
    )


def load_raw_users(spark) -> DataFrame:
    """Loads u.user with pipe delimiter and explicit schema."""
    return (
        spark.read
        .format("csv")
        .option("delimiter", "|")
        .schema(USERS_SCHEMA)
        .load(str(USERS_FILE))
    )


def clean_and_transform_ratings(df: DataFrame) -> DataFrame:
    """
    Validates rating boundaries, handles duplicates and missing values,
    and enriches with human-readable timestamp columns.
    """
    initial_count = df.count()

    # 1. Drop nulls in primary columns
    cleaned_df = df.dropna(subset=["user_id", "movie_id", "rating"])

    # 2. Filter ratings to valid 1.0 to 5.0 range
    cleaned_df = cleaned_df.filter((F.col("rating") >= 1.0) & (F.col("rating") <= 5.0))

    # 3. Deduplicate (user_id, movie_id), keeping the latest timestamp
    # Using window function or dropDuplicates sorted by timestamp
    cleaned_df = cleaned_df.dropDuplicates(subset=["user_id", "movie_id"])

    # 4. Add formatted datetime column
    cleaned_df = cleaned_df.withColumn(
        "rated_at",
        F.from_unixtime(F.col("timestamp")).cast("timestamp")
    )

    final_count = cleaned_df.count()
    dropped = initial_count - final_count
    print(f"Ratings cleaned: {final_count:,} valid records ({dropped} dropped).")
    return cleaned_df


def clean_and_transform_movies(df: DataFrame) -> DataFrame:
    """
    Collapses 19 binary genre columns into a clean array<string> column 'genres'.
    """
    # Build an array containing the genre name only if the indicator column == 1
    genre_exprs = [
        F.when(F.col(g) == 1, F.lit(g)).otherwise(None)
        for g in GENRE_COLUMNS
    ]

    # F.array_compact removes all None elements from the array
    movies_transformed = df.withColumn(
        "genres",
        F.array_compact(F.array(*genre_exprs))
    )

    # Select only essential clean columns
    return movies_transformed.select(
        "movie_id",
        "title",
        "release_date",
        "imdb_url",
        "genres"
    )


def split_train_test(ratings_df: DataFrame, train_ratio: float = 0.8, seed: int = 42):
    """
    Performs random split into training and test datasets.
    """
    train_df, test_df = ratings_df.randomSplit([train_ratio, 1.0 - train_ratio], seed=seed)
    return train_df, test_df


def run_pipeline():
    """Executes the full end-to-end data engineering pipeline."""
    print("=" * 70)
    print(" CineMatch Data Engineering & Preprocessing Pipeline")
    print("=" * 70)

    spark = get_spark_session(app_name="CineMatch-DataIngestion")
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Ingest Raw Datasets
    print("\n[Step 1/5] Loading raw MovieLens datasets with strict StructType schemas...")
    raw_ratings = load_raw_ratings(spark)
    raw_movies = load_raw_movies(spark)
    raw_users = load_raw_users(spark)

    print(f"  Raw ratings loaded: {raw_ratings.count():,}")
    print(f"  Raw movies loaded:  {raw_movies.count():,}")
    print(f"  Raw users loaded:   {raw_users.count():,}")

    # 2. Clean & Transform
    print("\n[Step 2/5] Cleaning and enriching datasets...")
    clean_ratings = clean_and_transform_ratings(raw_ratings)
    clean_movies = clean_and_transform_movies(raw_movies)
    clean_users = raw_users.dropna()

    # 3. Train/Test Split
    print("\n[Step 3/5] Splitting ratings into 80% Train / 20% Test partitions...")
    train_ratings, test_ratings = split_train_test(clean_ratings, train_ratio=0.8, seed=42)
    train_count = train_ratings.count()
    test_count = test_ratings.count()
    print(f"  Training set: {train_count:,} ratings ({train_count / clean_ratings.count() * 100:.1f}%)")
    print(f"  Testing set:  {test_count:,} ratings ({test_count / clean_ratings.count() * 100:.1f}%)")

    # 4. Export to Parquet
    print("\n[Step 4/5] Exporting clean DataFrames to optimized Parquet format...")
    clean_ratings.write.mode("overwrite").parquet(str(PROCESSED_DATA_DIR / "ratings.parquet"))
    clean_movies.write.mode("overwrite").parquet(str(PROCESSED_DATA_DIR / "movies.parquet"))
    clean_users.write.mode("overwrite").parquet(str(PROCESSED_DATA_DIR / "users.parquet"))
    train_ratings.write.mode("overwrite").parquet(str(PROCESSED_DATA_DIR / "train_ratings.parquet"))
    test_ratings.write.mode("overwrite").parquet(str(PROCESSED_DATA_DIR / "test_ratings.parquet"))
    print(f"  All Parquet files saved to: {PROCESSED_DATA_DIR}")

    # 5. Schema Preview
    print("\n[Step 5/5] Clean MovieLens Schema Inspection:")
    print("-" * 50)
    clean_movies.printSchema()
    print("-" * 50)
    print("Sample Movies with Extracted Genre Arrays:")
    clean_movies.show(5, truncate=False)

    spark.stop()
    print("\n Pipeline execution completed successfully!")


if __name__ == "__main__":
    run_pipeline()
