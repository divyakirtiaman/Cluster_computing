"""
Centralized Configuration for CineMatch Machine Learning Pipeline
"""

from pathlib import Path

# Base Paths
ML_ENGINE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = ML_ENGINE_DIR.parent
DATA_DIR = ML_ENGINE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw" / "ml-100k"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
MODELS_DIR = ML_ENGINE_DIR / "models"
CHECKPOINT_DIR = ML_ENGINE_DIR / "checkpoints"

# MovieLens 100K Files
RATINGS_FILE = RAW_DATA_DIR / "u.data"
MOVIES_FILE = RAW_DATA_DIR / "u.item"
USERS_FILE = RAW_DATA_DIR / "u.user"
GENRES_FILE = RAW_DATA_DIR / "u.genre"

# Spark MLlib ALS Hyperparameters
ALS_CONFIG = {
    "userCol": "user_id",
    "itemCol": "movie_id",
    "ratingCol": "rating",
    "rank": 10,                 # Number of latent factor dimensions (k)
    "maxIter": 10,              # Number of alternating iterations (converges cleanly)
    "regParam": 0.08,           # L2 regularization parameter (lambda)
    "coldStartStrategy": "drop",# Prevents NaN on unseen IDs during evaluation
    "nonnegative": True,        # Forces non-negative factors for better interpretability
    "checkpointInterval": 2,    # Truncates RDD DAG lineage every 2 iterations to prevent StackOverflow
    "seed": 42
}

# Evaluation Metric Targets
TARGET_METRICS = {
    "max_rmse": 0.95,
    "max_mae": 0.75,
    "top_k": 10
}
