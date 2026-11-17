"""
Strict PySpark Schemas for MovieLens 100K Dataset
Enforcing explicit StructType definitions avoids schema inference overhead,
guarantees type safety, and enables early fail-fast validation.
"""

from pyspark.sql.types import (
    StructType,
    StructField,
    IntegerType,
    FloatType,
    StringType,
    LongType
)

# 1. Ratings Schema (u.data: tab-separated)
# Format: user_id \t movie_id \t rating \t timestamp
RATINGS_SCHEMA = StructType([
    StructField("user_id", IntegerType(), nullable=False),
    StructField("movie_id", IntegerType(), nullable=False),
    StructField("rating", FloatType(), nullable=False),
    StructField("timestamp", LongType(), nullable=False)
])

# 2. Movies Schema (u.item: pipe-separated, latin-1)
# 24 columns: 5 metadata fields + 19 binary genre indicators
GENRE_COLUMNS = [
    "unknown", "Action", "Adventure", "Animation", "Childrens",
    "Comedy", "Crime", "Documentary", "Drama", "Fantasy",
    "Film_Noir", "Horror", "Musical", "Mystery", "Romance",
    "Sci_Fi", "Thriller", "War", "Western"
]

MOVIES_SCHEMA = StructType([
    StructField("movie_id", IntegerType(), nullable=False),
    StructField("title", StringType(), nullable=False),
    StructField("release_date", StringType(), nullable=True),
    StructField("video_release_date", StringType(), nullable=True),
    StructField("imdb_url", StringType(), nullable=True),
    *[StructField(genre, IntegerType(), nullable=False) for genre in GENRE_COLUMNS]
])

# 3. Users Schema (u.user: pipe-separated)
# Format: user_id | age | gender | occupation | zip_code
USERS_SCHEMA = StructType([
    StructField("user_id", IntegerType(), nullable=False),
    StructField("age", IntegerType(), nullable=False),
    StructField("gender", StringType(), nullable=False),
    StructField("occupation", StringType(), nullable=False),
    StructField("zip_code", StringType(), nullable=True)
])
