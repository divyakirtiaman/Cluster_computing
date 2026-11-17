"""
Exploratory Data Analysis (EDA) Pipeline for MovieLens 100K
Computes exact matrix sparsity, rating distributions, long-tail curves,
and statistical profiles using distributed PySpark SQL operations.
"""

from pyspark.sql import functions as F
from pyspark.sql import Window
from ml_engine.config import PROCESSED_DATA_DIR
from ml_engine.utils.spark_session import get_spark_session


def run_eda():
    spark = get_spark_session(app_name="CineMatch-EDA")

    print("=" * 70)
    print(" CineMatch Exploratory Data Analysis (EDA)")
    print("=" * 70)

    ratings_df = spark.read.parquet(str(PROCESSED_DATA_DIR / "ratings.parquet"))
    movies_df = spark.read.parquet(str(PROCESSED_DATA_DIR / "movies.parquet"))
    users_df = spark.read.parquet(str(PROCESSED_DATA_DIR / "users.parquet"))

    # 1. High-Level Dataset Volumes
    num_ratings = ratings_df.count()
    num_users = ratings_df.select("user_id").distinct().count()
    num_movies = ratings_df.select("movie_id").distinct().count()
    total_catalog_movies = movies_df.count()

    print(f"\n[1] Catalog & Interaction Volumes:")
    print(f"  Total Clean Ratings: {num_ratings:,}")
    print(f"  Unique Active Users: {num_users:,}")
    print(f"  Unique Rated Movies: {num_movies:,} (out of {total_catalog_movies:,} in catalog)")

    # 2. Exact Matrix Sparsity
    total_possible = num_users * num_movies
    sparsity = (1.0 - (num_ratings / total_possible)) * 100.0
    print(f"\n[2] Interaction Matrix Sparsity:")
    print(f"  Total Matrix Dimensions: {num_users:,} users x {num_movies:,} movies = {total_possible:,} cells")
    print(f"  Non-zero Observed Cells: {num_ratings:,}")
    print(f"  Matrix Sparsity:         {sparsity:.2f}% (Only {100 - sparsity:.2f}% observed)")

    # 3. Rating Distribution
    print(f"\n[3] Rating Distribution (1 to 5 Stars):")
    rating_dist = (
        ratings_df.groupBy("rating")
        .count()
        .orderBy("rating")
        .withColumn("percentage", F.round((F.col("count") / num_ratings) * 100, 2))
    )
    rating_dist.show()

    # 4. Rating Summary Statistics
    print(f"[4] Rating Descriptive Statistics:")
    ratings_df.select(
        F.round(F.mean("rating"), 2).alias("Mean_Rating"),
        F.round(F.stddev("rating"), 2).alias("Std_Dev"),
        F.min("rating").alias("Min_Rating"),
        F.max("rating").alias("Max_Rating")
    ).show()

    # 5. Top 10 Most Frequently Rated Movies (The Head of the Long Tail)
    print(f"[5] Top 10 Most Rated Movies:")
    top_rated = (
        ratings_df.groupBy("movie_id")
        .agg(
            F.count("rating").alias("total_ratings"),
            F.round(F.avg("rating"), 2).alias("avg_rating")
        )
        .join(movies_df.select("movie_id", "title", "genres"), on="movie_id")
        .orderBy(F.desc("total_ratings"))
        .limit(10)
    )
    top_rated.show(10, truncate=False)

    # 6. Top 10 Highest Rated Movies (Min. 50 Ratings)
    print(f"[6] Top 10 Highest Rated Movies (Minimum 50 Ratings Threshold):")
    best_movies = (
        ratings_df.groupBy("movie_id")
        .agg(
            F.count("rating").alias("rating_count"),
            F.round(F.avg("rating"), 2).alias("avg_rating")
        )
        .filter(F.col("rating_count") >= 50)
        .join(movies_df.select("movie_id", "title"), on="movie_id")
        .orderBy(F.desc("avg_rating"), F.desc("rating_count"))
        .limit(10)
    )
    best_movies.show(10, truncate=False)

    # 7. User Activity Distribution
    print(f"[7] User Activity Profiling:")
    user_activity = (
        ratings_df.groupBy("user_id")
        .agg(F.count("rating").alias("num_ratings"))
    )
    user_activity.select(
        F.min("num_ratings").alias("Min_Ratings_Per_User"),
        F.round(F.avg("num_ratings"), 1).alias("Avg_Ratings_Per_User"),
        F.max("num_ratings").alias("Max_Ratings_Per_User")
    ).show()

    spark.stop()
    print("=" * 70)
    print(" Exploratory Data Analysis Complete!")
    print("=" * 70)


if __name__ == "__main__":
    run_eda()
