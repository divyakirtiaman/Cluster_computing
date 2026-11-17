"""
Automated Test Suite for CineMatch FastAPI Backend
Tests Health Probes, Auth flows, Movies Catalog, Batch Recommendations,
Similar Movies, and Real-Time Rating Prediction.
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "CineMatch" in data["service"]


def test_auth_registration_and_login():
    # 1. Register new user
    user_payload = {
        "email": "tester@cinematch.com",
        "username": "tester",
        "password": "Password123!",
        "preferred_genres": ["Action", "Sci-Fi"]
    }
    reg_res = client.post("/api/v1/auth/register", json=user_payload)
    assert reg_res.status_code in [201, 400]  # 201 or already exists

    # 2. Login
    login_payload = {
        "email": "tester@cinematch.com",
        "password": "Password123!"
    }
    login_res = client.post("/api/v1/auth/login", json=login_payload)
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert "access_token" in login_data
    assert login_data["token_type"] == "bearer"
    token = login_data["access_token"]

    # 3. Access Protected /me profile
    headers = {"Authorization": f"Bearer {token}"}
    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["email"] == "tester@cinematch.com"

    # 4. Unauthorized without token
    unauth_res = client.get("/api/v1/auth/me")
    assert unauth_res.status_code == 401


def test_movies_catalog_and_search():
    # 1. List movies
    res = client.get("/api/v1/movies/?limit=10")
    assert res.status_code == 200
    movies = res.json()
    assert len(movies) == 10
    assert "title" in movies[0]

    # 2. Search for "Star Wars"
    search_res = client.get("/api/v1/movies/?search=Star%20Wars")
    assert search_res.status_code == 200
    search_movies = search_res.json()
    assert len(search_movies) >= 1
    assert any("Star Wars" in m["title"] for m in search_movies)

    # 3. Filter by genre
    genre_res = client.get("/api/v1/movies/?genre=Animation&limit=5")
    assert genre_res.status_code == 200
    for m in genre_res.json():
        assert "Animation" in m["genres"]

    # 4. Specific movie detail
    movie_res = client.get("/api/v1/movies/50")
    assert movie_res.status_code == 200
    movie_data = movie_res.json()
    assert movie_data["movie_id"] == 50
    assert "Star Wars" in movie_data["title"]


def test_user_recommendations():
    # Fetch top 10 recommendations for User 1
    res = client.get("/api/v1/recommendations/user/1?limit=10")
    assert res.status_code == 200
    data = response = res.json()
    assert data["user_id"] == 1
    assert data["algorithm"] == "ALS-MatrixFactorization"
    assert len(data["recommendations"]) == 10
    assert "predicted_rating" in data["recommendations"][0]


def test_similar_movies():
    # Fetch similar movies for Star Wars (movie_id = 50)
    res = client.get("/api/v1/recommendations/movie/50/similar?limit=5")
    assert res.status_code == 200
    data = res.json()
    assert data["source_movie_id"] == 50
    assert len(data["similar_movies"]) == 5
    # Empire Strikes Back should be the top match
    top_similar_title = data["similar_movies"][0]["title"]
    assert "Empire Strikes Back" in top_similar_title


def test_realtime_rating_prediction():
    # Real-time dot-product prediction for user 1 and movie 50
    payload = {"user_id": 1, "movie_id": 50}
    res = client.post("/api/v1/recommendations/predict", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["user_id"] == 1
    assert data["movie_id"] == 50
    assert 1.0 <= data["predicted_rating"] <= 5.0
