"""
Apache Spark MLlib ALS Model Training Pipeline
Trains an Alternating Least Squares (ALS) Matrix Factorization model on the training set,
extracts latent user & item factor matrices, and persists model artifacts.
"""

import time
from pathlib import Path
from pyspark.ml.recommendation import ALS, ALSModel
from pyspark.sql import functions as F

from ml_engine.config import (
    PROCESSED_DATA_DIR,
    MODELS_DIR,
    CHECKPOINT_DIR,
    ALS_CONFIG
)
from ml_engine.utils.spark_session import get_spark_session


def train_als_model(train_df, config: dict = ALS_CONFIG) -> ALSModel:
    """
    Instantiates and fits a PySpark MLlib ALS model.
    """
    print(f"Initializing ALS with hyperparameters:")
    print(f"  rank (latent factors k) : {config['rank']}")
    print(f"  maxIter (iterations)    : {config['maxIter']}")
    print(f"  regParam (L2 lambda)    : {config['regParam']}")
    print(f"  coldStartStrategy       : {config['coldStartStrategy']}")
    print(f"  nonnegative             : {config['nonnegative']}")
    print(f"  checkpointInterval      : {config.get('checkpointInterval', 2)}")

    als = ALS(
        userCol=config["userCol"],
        itemCol=config["itemCol"],
        ratingCol=config["ratingCol"],
        rank=config["rank"],
        maxIter=config["maxIter"],
        regParam=config["regParam"],
        coldStartStrategy=config["coldStartStrategy"],
        nonnegative=config["nonnegative"],
        checkpointInterval=config.get("checkpointInterval", 2),
        seed=config.get("seed", 42)
    )

    start_time = time.time()
    model = als.fit(train_df)
    elapsed = time.time() - start_time
    print(f"ALS model training completed in {elapsed:.2f} seconds.")
    return model


def run_training_pipeline():
    print("=" * 70)
    print(" CineMatch ML Recommendation Engine — ALS Training Pipeline")
    print("=" * 70)

    spark = get_spark_session(app_name="CineMatch-ALSTraining")
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    spark.sparkContext.setCheckpointDir(str(CHECKPOINT_DIR))

    # 1. Load Training Dataset
    train_path = PROCESSED_DATA_DIR / "train_ratings.parquet"
    print(f"\n[Step 1/4] Loading training partition from {train_path}...")
    train_df = spark.read.parquet(str(train_path)).cache()
    print(f"  Loaded {train_df.count():,} training interactions.")

    # 2. Train ALS Model
    print("\n[Step 2/4] Fitting distributed ALS Matrix Factorization model...")
    als_model = train_als_model(train_df, ALS_CONFIG)

    # 3. Save Model Artifact
    model_save_path = MODELS_DIR / "als_model"
    print(f"\n[Step 3/4] Persisting trained ALS model to {model_save_path}...")
    als_model.write().overwrite().save(str(model_save_path))
    print("  Model saved successfully.")

    # 4. Extract and Save Latent Factors
    print("\n[Step 4/4] Extracting and exporting latent factor matrices...")
    user_factors = als_model.userFactors
    item_factors = als_model.itemFactors

    user_count = user_factors.count()
    item_count = item_factors.count()
    print(f"  User Factors: {user_count:,} vectors of dimension {ALS_CONFIG['rank']}")
    print(f"  Item Factors: {item_count:,} vectors of dimension {ALS_CONFIG['rank']}")

    user_factors.write.mode("overwrite").parquet(str(PROCESSED_DATA_DIR / "user_factors.parquet"))
    item_factors.write.mode("overwrite").parquet(str(PROCESSED_DATA_DIR / "item_factors.parquet"))
    print(f"  Latent factors saved to {PROCESSED_DATA_DIR}")

    # Inspect sample latent factors
    print("\nSample Item Latent Factors (Movie ID + 10D Factor Vector):")
    item_factors.show(5, truncate=False)

    train_df.unpersist()
    spark.stop()
    print("=" * 70)
    print(" ALS Training Pipeline Completed Successfully!")
    print("=" * 70)


if __name__ == "__main__":
    run_training_pipeline()
