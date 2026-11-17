"""
SparkSession Factory for CineMatch
Provides resilient, cross-platform SparkSession creation with optimized local execution parameters.
"""

import os
import sys
import platform
from pathlib import Path
from pyspark.sql import SparkSession


def setup_windows_hadoop():
    """Sets HADOOP_HOME to bundled winutils on Windows if not already defined."""
    if platform.system() == "Windows":
        project_hadoop = Path(__file__).resolve().parent.parent / "hadoop"
        if (project_hadoop / "bin" / "winutils.exe").exists():
            os.environ["HADOOP_HOME"] = str(project_hadoop)
            bin_dir = str(project_hadoop / "bin")
            if bin_dir not in os.environ.get("PATH", ""):
                os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")


def get_spark_session(app_name: str = "CineMatch-Engine", memory: str = "4g") -> SparkSession:
    """
    Initializes and returns an optimized SparkSession for local execution.
    Configures memory, partition parallelism, Windows Hadoop paths, and suppresses verbose driver logging.
    """
    setup_windows_hadoop()

    builder = (
        SparkSession.builder
        .appName(app_name)
        .master("local[*]")
        .config("spark.driver.memory", memory)
        .config("spark.executor.memory", memory)
        .config("spark.sql.shuffle.partitions", "8")
        .config("spark.default.parallelism", "8")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .config("spark.ui.enabled", "false")
        .config("spark.driver.extraJavaOptions", "-Xss8m")
        .config("spark.executor.extraJavaOptions", "-Xss8m")
        .config("spark.hadoop.fs.file.impl", "org.apache.hadoop.fs.LocalFileSystem")
        .config("spark.hadoop.mapreduce.fileoutputcommitter.algorithm.version", "2")
    )

    spark = builder.getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    return spark
