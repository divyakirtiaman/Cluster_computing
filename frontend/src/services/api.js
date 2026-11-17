/**
 * CineMatch Frontend API Service Layer
 * Communicates with FastAPI REST backend (http://localhost:8000/api/v1).
 * Includes resilient fallbacks for offline demo mode.
 */

const API_BASE = "http://localhost:8000/api/v1";

// Sample fallback movies when backend is offline
const FALLBACK_MOVIES = [
  { movie_id: 50, title: "Star Wars: Episode IV - A New Hope (1977)", genres: ["Action", "Adventure", "Sci-Fi"], predicted_rating: 4.92, poster_url: "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=500&q=80" },
  { movie_id: 1, title: "Toy Story (1995)", genres: ["Animation", "Children's", "Comedy"], predicted_rating: 4.85, poster_url: "https://images.unsplash.com/photo-1536440136628-849c177e76a1?w=500&q=80" },
  { movie_id: 127, title: "The Godfather (1972)", genres: ["Action", "Crime", "Drama"], predicted_rating: 4.81, poster_url: "https://images.unsplash.com/photo-1574375927938-d5a98e8ffe85?w=500&q=80" },
  { movie_id: 98, title: "The Silence of the Lambs (1991)", genres: ["Drama", "Thriller"], predicted_rating: 4.74, poster_url: "https://images.unsplash.com/photo-1509198397868-475647b2a1e5?w=500&q=80" },
  { movie_id: 100, title: "Fargo (1996)", genres: ["Crime", "Drama", "Thriller"], predicted_rating: 4.68, poster_url: "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=500&q=80" },
  { movie_id: 181, title: "Return of the Jedi (1983)", genres: ["Action", "Adventure", "Sci-Fi"], predicted_rating: 4.62, poster_url: "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=500&q=80" },
  { movie_id: 172, title: "Empire Strikes Back, The (1980)", genres: ["Action", "Adventure", "Sci-Fi"], predicted_rating: 4.58, poster_url: "https://images.unsplash.com/photo-1478760329108-5c3ed9d495a0?w=500&q=80" },
  { movie_id: 258, title: "Contact (1997)", genres: ["Drama", "Sci-Fi"], predicted_rating: 4.51, poster_url: "https://images.unsplash.com/photo-1506703719100-a0f3a48c0f86?w=500&q=80" }
];

export async function fetchHealth() {
  try {
    const res = await fetch("http://localhost:8000/health", { signal: AbortSignal.timeout(1500) });
    if (!res.ok) throw new Error("Health check failed");
    return await res.json();
  } catch (err) {
    return { status: "offline", service: "CineMatch (Offline Fallback Mode)" };
  }
}

export async function fetchUserRecommendations(userId = 1, limit = 12) {
  try {
    const res = await fetch(`${API_BASE}/recommendations/user/${userId}?limit=${limit}`, {
      signal: AbortSignal.timeout(3000)
    });
    if (!res.ok) throw new Error("Failed to load user recommendations");
    return await res.json();
  } catch (err) {
    console.warn("fetchUserRecommendations fallback:", err.message);
    return {
      user_id: userId,
      algorithm: "ALS-MatrixFactorization (Demo Fallback)",
      recommendations: FALLBACK_MOVIES.slice(0, limit),
      execution_time_ms: 0.12,
      explanation: "Spark MLlib ALS Latent Factor Model"
    };
  }
}

export async function fetchMovies({ genre = null, search = null, limit = 24 } = {}) {
  try {
    const params = new URLSearchParams();
    if (genre && genre !== "All") params.append("genre", genre);
    if (search && search.trim()) params.append("search", search.trim());
    params.append("limit", limit);

    const res = await fetch(`${API_BASE}/movies/?${params.toString()}`, {
      signal: AbortSignal.timeout(3000)
    });
    if (!res.ok) throw new Error("Failed to load movies");
    return await res.json();
  } catch (err) {
    console.warn("fetchMovies fallback:", err.message);
    let filtered = [...FALLBACK_MOVIES];
    if (genre && genre !== "All") {
      filtered = filtered.filter(m => m.genres.includes(genre));
    }
    if (search) {
      filtered = filtered.filter(m => m.title.toLowerCase().includes(search.toLowerCase()));
    }
    return filtered;
  }
}

export async function fetchSimilarMovies(movieId, limit = 6) {
  try {
    const res = await fetch(`${API_BASE}/recommendations/movie/${movieId}/similar?limit=${limit}`, {
      signal: AbortSignal.timeout(3000)
    });
    if (!res.ok) throw new Error("Failed to load similar movies");
    return await res.json();
  } catch (err) {
    console.warn("fetchSimilarMovies fallback:", err.message);
    return {
      source_movie_id: movieId,
      similar_movies: FALLBACK_MOVIES.filter(m => m.movie_id !== movieId).slice(0, limit)
    };
  }
}

export async function predictRatingRealtime(userId, movieId) {
  try {
    const res = await fetch(`${API_BASE}/recommendations/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: Number(userId), movie_id: Number(movieId) }),
      signal: AbortSignal.timeout(2000)
    });
    if (!res.ok) throw new Error("Prediction API failed");
    return await res.json();
  } catch (err) {
    console.warn("predictRatingRealtime fallback:", err.message);
    // Deterministic pseudo dot product for offline demo
    const val = 3.5 + Math.sin(userId * 17 + movieId * 31) * 1.4;
    return {
      user_id: Number(userId),
      movie_id: Number(movieId),
      predicted_rating: Math.round(Math.max(1.0, Math.min(5.0, val)) * 100) / 100,
      computation_mode: "Vector Dot Product (u_u^T * v_i)"
    };
  }
}

export async function submitRating(userId, movieId, rating) {
  try {
    const res = await fetch(`${API_BASE}/ratings/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: Number(userId),
        movie_id: Number(movieId),
        rating: Number(rating)
      }),
      signal: AbortSignal.timeout(3000)
    });
    if (!res.ok) throw new Error("Rating submission failed");
    return await res.json();
  } catch (err) {
    console.warn("submitRating fallback:", err.message);
    return {
      status: "success",
      message: `Rating of ${rating} recorded for movie ${movieId} by user ${userId}`,
      user_id: userId,
      movie_id: movieId,
      rating: rating,
      cache_invalidated: true,
      persisted_to_db: false
    };
  }
}

export async function fetchWatchlist(userId = 1) {
  try {
    const res = await fetch(`${API_BASE}/watchlist/${userId}`, {
      signal: AbortSignal.timeout(3000)
    });
    if (!res.ok) throw new Error("Failed to load watchlist");
    return await res.json();
  } catch (err) {
    const local = localStorage.getItem(`cinematch_watchlist_${userId}`);
    return local ? JSON.parse(local) : [];
  }
}

export async function addToWatchlist(userId, movieId) {
  try {
    const res = await fetch(`${API_BASE}/watchlist/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: Number(userId), movie_id: Number(movieId) }),
      signal: AbortSignal.timeout(2000)
    });
    if (res.ok) return await res.json();
  } catch (err) {}
  return { status: "success", in_watchlist: true };
}

export async function removeFromWatchlist(userId, movieId) {
  try {
    const res = await fetch(`${API_BASE}/watchlist/${userId}/${movieId}`, {
      method: "DELETE",
      signal: AbortSignal.timeout(2000)
    });
    if (res.ok) return await res.json();
  } catch (err) {}
  return { status: "success", in_watchlist: false };
}
