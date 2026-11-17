"""
MovieLens 100K Dataset Downloader & Validator for CineMatch
Source: GroupLens Research (University of Minnesota)
"""

import os
import ssl
import urllib.request
import urllib.error
import zipfile
from pathlib import Path

MOVIELENS_URL = "https://files.grouplens.org/datasets/movielens/ml-100k.zip"
TARGET_DIR = Path(__file__).resolve().parent.parent / "ml_engine" / "data" / "raw"
ZIP_FILE = TARGET_DIR / "ml-100k.zip"
EXTRACTED_DIR = TARGET_DIR / "ml-100k"


def download_and_extract():
    TARGET_DIR.mkdir(parents=True, exist_ok=True)

    if EXTRACTED_DIR.exists() and (EXTRACTED_DIR / "u.data").exists():
        print(f"MovieLens 100K dataset already exists at {EXTRACTED_DIR}")
    else:
        print(f"Downloading MovieLens 100K from {MOVIELENS_URL}...")
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        req = urllib.request.Request(MOVIELENS_URL, headers=headers)
        try:
            context = ssl.create_default_context()
            with urllib.request.urlopen(req, context=context) as response, open(ZIP_FILE, "wb") as out_file:
                shutil_copy = response.read()
                out_file.write(shutil_copy)
        except (ssl.SSLError, urllib.error.URLError, Exception) as exc:
            print(f"Standard SSL verification failed ({exc}). Retrying with unverified SSL context...")
            unverified_ctx = ssl._create_unverified_context()
            with urllib.request.urlopen(req, context=unverified_ctx) as response, open(ZIP_FILE, "wb") as out_file:
                shutil_copy = response.read()
                out_file.write(shutil_copy)
        print(f"Downloaded {len(shutil_copy):,} bytes. Extracting archive...")

        with zipfile.ZipFile(ZIP_FILE, "r") as zip_ref:
            zip_ref.extractall(TARGET_DIR)
        print("Extraction complete.")

    # Validation
    expected_files = ["u.data", "u.item", "u.user", "u.genre", "u.info"]
    print("\nDataset Verification Summary:")
    print("-" * 50)
    for fname in expected_files:
        fpath = EXTRACTED_DIR / fname
        if fpath.exists():
            line_count = sum(1 for _ in open(fpath, "r", encoding="latin-1"))
            print(f"  {fname:<10} : {line_count:>7} records ({fpath.stat().st_size:,} bytes)")
        else:
            print(f"  {fname:<10} : MISSING")
    print("-" * 50)
    print("MovieLens 100K dataset is ready for PySpark ingestion!")


if __name__ == "__main__":
    download_and_extract()
