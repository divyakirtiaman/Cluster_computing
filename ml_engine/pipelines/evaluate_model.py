"""
Machine Learning Evaluation Pipeline for CineMatch
Computes standard recommendation metrics: RMSE, MAE, Precision@K, Recall@K, NDCG@K,
Catalog Coverage, and runs a multi-configuration benchmark comparison.
"""

import math
from pathlib import Path
from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.ml.recommendation import ALS, ALSModel
from pyspark.sql import functions as F
from pyspark.sql.window import Window

from ml_engine.config import (
    PROCESSED_DATA_DIR,
    MODELS_DIR,
    CHECKPOINT_DIR,
    ALS_CONFIG
)
from ml_engine.utils.spark_session import get_spark_session


def evaluate_prediction_error(model: ALSModel, test_df):
    """
    Evaluates RMSE and MAE on the holdout test set using PySpark RegressionEvaluator.
    """
    print("\n--- Evaluating Rating Prediction Error on Test Set (20,099 ratings) ---")
    predictions = model.transform(test_df).cache()

    rmse_eval = RegressionEvaluator(metricName="rmse", labelCol="rating", predictionCol="prediction")
    mae_eval = RegressionEvaluator(metricName="mae", labelCol="rating", predictionCol="prediction")

    rmse = rmse_eval.evaluate(predictions)
    mae = mae_eval.evaluate(predictions)

    print(f"  Root Mean Squared Error (RMSE): {rmse:.4f}")
    print(f"  Mean Absolute Error (MAE)      : {mae:.4f}")

    # Inspect sample test predictions vs actual ratings
    print("\nSample Actual vs. Predicted Ratings on Holdout Test Set:")
    predictions.select("user_id", "movie_id", "rating", F.round("prediction", 2).alias("predicted_rating")).show(5)

    predictions.unpersist()
    return rmse, mae


def evaluate_ranking_metrics(model: ALSModel, train_df, test_df, k: int = 10, relevance_threshold: float = 4.0):
    """
    Computes Precision@K, Recall@K, and NDCG@K on the holdout test set.
    A test rating >= relevance_threshold (e.g. 4.0 stars) is classified as a relevant hit.
    """
    print(f"\n--- Evaluating Top-{k} Ranking Metrics (Threshold: rating >= {relevance_threshold}) ---")

    # 1. Ground truth relevant items per user from test set
    relevant_test = (
        test_df.filter(F.col("rating") >= relevance_threshold)
        .groupBy("user_id")
        .agg(F.collect_set("movie_id").alias("ground_truth"))
        .filter(F.size("ground_truth") > 0)
    ).cache()

    test_user_count = relevant_test.count()

    # 2. Top-K recommendations for these test users
    all_recs = model.recommendForUserSubset(relevant_test.select("user_id"), k).cache()

    # 3. Extract recommended movie IDs as array
    recs_extracted = all_recs.select(
        F.col("user_id"),
        F.expr("transform(recommendations, x -> x.movie_id)").alias("rec_ids")
    )

    # 4. Join ground truth with recommendations
    eval_joined = relevant_test.join(recs_extracted, on="user_id").collect()

    precisions = []
    recalls = []
    ndcgs = []

    for row in eval_joined:
        truth = set(row["ground_truth"])
        recs = row["rec_ids"][:k]

        # Hits in top-k
        hits = [1 if m in truth else 0 for m in recs]
        num_hits = sum(hits)

        # Precision@K
        p_at_k = num_hits / float(k)
        precisions.append(p_at_k)

        # Recall@K
        r_at_k = num_hits / float(len(truth)) if truth else 0.0
        recalls.append(r_at_k)

        # NDCG@K
        # DCG = sum(hit_i / log2(i + 1))
        dcg = sum(hit / math.log2(idx + 2) for idx, hit in enumerate(hits))
        # IDCG = ideal DCG where all min(len(truth), k) hits are at top ranks
        ideal_hits = min(len(truth), k)
        idcg = sum(1.0 / math.log2(idx + 2) for idx in range(ideal_hits))
        ndcg = (dcg / idcg) if idcg > 0 else 0.0
        ndcgs.append(ndcg)

    avg_precision = sum(precisions) / len(precisions) if precisions else 0.0
    avg_recall = sum(recalls) / len(recalls) if recalls else 0.0
    avg_ndcg = sum(ndcgs) / len(ndcgs) if ndcgs else 0.0

    print(f"  Precision@{k} : {avg_precision:.4f} ({avg_precision * 100:.2f}% of top-{k} recommendations were relevant)")
    print(f"  Recall@{k}    : {avg_recall:.4f} ({avg_recall * 100:.2f}% of user's liked test movies captured)")
    print(f"  NDCG@{k}      : {avg_ndcg:.4f} (Ranking quality score)")

    relevant_test.unpersist()
    all_recs.unpersist()
    return avg_precision, avg_recall, avg_ndcg


def evaluate_catalog_coverage(spark, k: int = 10):
    """
    Calculates Catalog Coverage: fraction of unique catalog items recommended across all users.
    """
    print(f"\n--- Evaluating Catalog Coverage (Top-{k} Recommendations) ---")
    movies_df = spark.read.parquet(str(PROCESSED_DATA_DIR / "movies.parquet"))
    recs_df = spark.read.parquet(str(PROCESSED_DATA_DIR / "top_recommendations.parquet"))

    total_catalog = movies_df.select("movie_id").distinct().count()
    recommended_unique = recs_df.select("movie_id").distinct().count()

    coverage_pct = (recommended_unique / total_catalog) * 100.0
    print(f"  Total Catalog Movies : {total_catalog:,}")
    print(f"  Surfaced in Top-{k}   : {recommended_unique:,} unique movies")
    print(f"  Catalog Coverage     : {coverage_pct:.2f}%")
    return coverage_pct


def compare_hyperparameter_configurations(spark, train_df, test_df):
    """
    Compares 3 different ALS hyperparameter configurations across RMSE and MAE.
    """
    print("\n" + "=" * 70)
    print(" Hyperparameter Configuration Benchmark Comparison")
    print("=" * 70)

    configs = [
        {"name": "Config A (Low Rank)", "rank": 5, "regParam": 0.10, "maxIter": 10},
        {"name": "Config B (Baseline)", "rank": 10, "regParam": 0.08, "maxIter": 10},
        {"name": "Config C (High Rank)", "rank": 20, "regParam": 0.05, "maxIter": 10},
    ]

    results = []
    rmse_eval = RegressionEvaluator(metricName="rmse", labelCol="rating", predictionCol="prediction")
    mae_eval = RegressionEvaluator(metricName="mae", labelCol="rating", predictionCol="prediction")

    for cfg in configs:
        als = ALS(
            userCol="user_id",
            itemCol="movie_id",
            ratingCol="rating",
            rank=cfg["rank"],
            regParam=cfg["regParam"],
            maxIter=cfg["maxIter"],
            coldStartStrategy="drop",
            nonnegative=True,
            checkpointInterval=2,
            seed=42
        )
        model = als.fit(train_df)
        preds = model.transform(test_df)
        rmse = rmse_eval.evaluate(preds)
        mae = mae_eval.evaluate(preds)
        results.append((cfg["name"], cfg["rank"], cfg["regParam"], round(rmse, 4), round(mae, 4)))

    print(f"\n{'Configuration':<25} | {'Rank (k)':<10} | {'RegParam':<10} | {'Test RMSE':<10} | {'Test MAE':<10}")
    print("-" * 75)
    for name, rank, reg, rmse, mae in results:
        print(f"{name:<25} | {rank:<10} | {reg:<10} | {rmse:<10} | {mae:<10}")
    print("-" * 75)


def run_evaluation_suite():
    print("=" * 70)
    print(" CineMatch Phase 5: Machine Learning Evaluation Suite")
    print("=" * 70)

    spark = get_spark_session(app_name="CineMatch-Evaluation")
    spark.sparkContext.setCheckpointDir(str(CHECKPOINT_DIR))

    train_df = spark.read.parquet(str(PROCESSED_DATA_DIR / "train_ratings.parquet")).cache()
    test_df = spark.read.parquet(str(PROCESSED_DATA_DIR / "test_ratings.parquet")).cache()

    model_path = MODELS_DIR / "als_model"
    model = ALSModel.load(str(model_path))

    # 1. Rating Prediction Error
    rmse, mae = evaluate_prediction_error(model, test_df)

    # 2. Ranking Relevance Metrics
    precision, recall, ndcg = evaluate_ranking_metrics(model, train_df, test_df, k=10)

    # 3. Catalog Coverage
    coverage = evaluate_catalog_coverage(spark, k=10)

    # 4. Multi-Configuration Benchmark Comparison
    compare_hyperparameter_configurations(spark, train_df, test_df)

    train_df.unpersist()
    test_df.unpersist()
    spark.stop()
    print("\n Evaluation Suite Execution Completed Successfully!")


if __name__ == "__main__":
    run_evaluation_suite()
