"""
Batch Recommendation & Item-to-Item Similarity Engine
Precomputes Top-N personalized recommendations for all users and generates
item-to-item semantic similarity tables using latent factor cosine similarity.
"""

import math
from pathlib import Path
from pyspark.ml.recommendation import ALSModel
from pyspark.sql import functions as F
from pyspark.sql.types import (
    ArrayType,
    StructType,
    StructField,
    IntegerType,
    StringType,
    FloatType
)

from ml_engine.config import PROCESSED_DATA_DIR, MODELS_DIR
from ml_engine.utils.spark_session import get_spark_session


def compute_item_similarity(spark, item_factors_df, movies_df, top_k: int = 5):
    """
    Computes pairwise Cosine Similarity between movie latent factor vectors.
    Returns the top-K most similar movies for every movie in the catalog.
    """
    print(f"\nComputing pairwise Cosine Similarity across {item_factors_df.count()} movie factor vectors...")

    # Collect factor vectors into memory dictionary for efficient vectorized cosine computation
    # (Since catalog size is 1,682 movies with 10 dimensions, this takes < 1 MB of memory!)
    factors_raw = item_factors_df.select("id", "features").collect()
    movie_vectors = {}
    for row in factors_raw:
        vec = row["features"]
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            movie_vectors[row["id"]] = (vec, norm)

    # Compute top-K similar items for each movie
    similar_records = []
    movie_ids = list(movie_vectors.keys())

    for m_id, (v1, norm1) in movie_vectors.items():
        scores = []
        for other_id in movie_ids:
            if other_id == m_id:
                continue
            v2, norm2 = movie_vectors[other_id]
            dot_product = sum(a * b for a, b in zip(v1, v2))
            sim = dot_product / (norm1 * norm2)
            scores.append((other_id, float(sim)))

        # Sort descending by cosine similarity and take top-K
        scores.sort(key=lambda x: x[1], reverse=True)
        for rank, (sim_id, sim_score) in enumerate(scores[:top_k], 1):
            similar_records.append((m_id, sim_id, sim_score, rank))

    # Convert to Spark DataFrame
    schema = StructType([
        StructField("source_movie_id", IntegerType(), False),
        StructField("similar_movie_id", IntegerType(), False),
        StructField("similarity_score", FloatType(), False),
        StructField("rank", IntegerType(), False)
    ])

    sim_df = spark.createDataFrame(similar_records, schema=schema)

    # Enrich with movie titles
    movies_meta = movies_df.select(
        F.col("movie_id").alias("similar_movie_id"),
        F.col("title").alias("similar_title"),
        F.col("genres").alias("similar_genres")
    )
    enriched_sim = (
        sim_df.join(movies_meta, on="similar_movie_id")
        .join(
            movies_df.select(F.col("movie_id").alias("source_movie_id"), F.col("title").alias("source_title")),
            on="source_movie_id"
        )
        .orderBy("source_movie_id", "rank")
    )

    return enriched_sim


def run_recommendation_generation():
    print("=" * 70)
    print(" CineMatch Batch Recommendation & Item Similarity Pipeline")
    print("=" * 70)

    spark = get_spark_session(app_name="CineMatch-RecGeneration")

    # 1. Load Trained Model & Metadata
    model_path = MODELS_DIR / "als_model"
    print(f"\n[Step 1/4] Loading trained ALS model from {model_path}...")
    als_model = ALSModel.load(str(model_path))
    movies_df = spark.read.parquet(str(PROCESSED_DATA_DIR / "movies.parquet")).cache()

    # 2. Generate Top-10 Recommendations for All Users
    print("\n[Step 2/4] Generating Top-10 personalized recommendations for all users...")
    user_recs = als_model.recommendForAllUsers(10)

    # Explode recommendations array into individual rows
    exploded_recs = (
        user_recs
        .select(
            F.col("user_id"),
            F.posexplode(F.col("recommendations")).alias("rank", "rec")
        )
        .select(
            F.col("user_id"),
            (F.col("rank") + 1).alias("rank"),
            F.col("rec.movie_id").alias("movie_id"),
            F.round(F.col("rec.rating"), 2).alias("predicted_rating")
        )
    )

    # Join with movie metadata to attach title, genres, release date
    enriched_recs = (
        exploded_recs
        .join(movies_df, on="movie_id")
        .select(
            "user_id",
            "rank",
            "movie_id",
            "title",
            "genres",
            "predicted_rating"
        )
        .orderBy("user_id", "rank")
    )

    # 3. Save Top Recommendations
    recs_save_path = PROCESSED_DATA_DIR / "top_recommendations.parquet"
    print(f"\n[Step 3/4] Exporting top recommendations to {recs_save_path}...")
    enriched_recs.write.mode("overwrite").parquet(str(recs_save_path))
    print(f"  Precomputed {enriched_recs.count():,} recommendation entries.")

    # Preview sample recommendations for User 1
    print("\nTop 10 Recommendations for User #1:")
    print("-" * 70)
    enriched_recs.filter(F.col("user_id") == 1).show(10, truncate=False)

    # 4. Generate Item-to-Item Similarities
    print("\n[Step 4/4] Generating Item-to-Item Similarity Tables...")
    item_factors_df = spark.read.parquet(str(PROCESSED_DATA_DIR / "item_factors.parquet"))
    item_similarity_df = compute_item_similarity(spark, item_factors_df, movies_df, top_k=5)

    sim_save_path = PROCESSED_DATA_DIR / "similar_movies.parquet"
    item_similarity_df.write.mode("overwrite").parquet(str(sim_save_path))
    print(f"  Item similarity table saved to {sim_save_path}")

    # Preview similar movies for "Star Wars (1977)" (movie_id = 50)
    print("\nMovies Most Similar to 'Star Wars (1977)' (Based on Latent Factor Cosine Similarity):")
    print("-" * 70)
    (
        item_similarity_df
        .filter(F.col("source_movie_id") == 50)
        .select("rank", "similar_movie_id", "similar_title", "similar_genres", F.round("similarity_score", 4).alias("cosine_sim"))
        .show(5, truncate=False)
    )

    movies_df.unpersist()
    spark.stop()
    print("=" * 70)
    print(" Recommendation Generation Pipeline Completed Successfully!")
    print("=" * 70)


if __name__ == "__main__":
    run_recommendation_generation()
