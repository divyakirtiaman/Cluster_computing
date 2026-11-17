import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import MovieCard from './components/MovieCard';
import Footer from './components/Footer';
import RatingModal from './components/RatingModal';
import SimilarMoviesModal from './components/SimilarMoviesModal';
import RealtimePredictorModal from './components/RealtimePredictorModal';
import WatchlistDrawer from './components/WatchlistDrawer';
import MovieDetailModal from './components/MovieDetailModal';
import {
  fetchUserRecommendations,
  fetchMovies,
  fetchHealth,
  fetchWatchlist,
  addToWatchlist,
  removeFromWatchlist
} from './services/api';
import { Sparkles, TrendingUp, Filter, Zap, Database, CheckCircle2, RefreshCw } from 'lucide-react';

const GENRES = [
  "All",
  "Action",
  "Adventure",
  "Animation",
  "Children's",
  "Comedy",
  "Crime",
  "Documentary",
  "Drama",
  "Fantasy",
  "Film-Noir",
  "Horror",
  "Musical",
  "Mystery",
  "Romance",
  "Sci-Fi",
  "Thriller",
  "War",
  "Western"
];

export default function App() {
  const [currentUserId, setCurrentUserId] = useState(1);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedGenre, setSelectedGenre] = useState("All");

  // Recommendation State
  const [recommendations, setRecommendations] = useState([]);
  const [recMeta, setRecMeta] = useState(null);
  const [loadingRecs, setLoadingRecs] = useState(true);

  // Catalog State
  const [catalogMovies, setCatalogMovies] = useState([]);
  const [loadingCatalog, setLoadingCatalog] = useState(true);

  // Watchlist State
  const [watchlist, setWatchlist] = useState([]);
  const [isWatchlistOpen, setIsWatchlistOpen] = useState(false);

  // Modals
  const [ratingMovie, setRatingMovie] = useState(null);
  const [similarMovie, setSimilarMovie] = useState(null);
  const [isPredictorOpen, setIsPredictorOpen] = useState(false);
  const [detailMovie, setDetailMovie] = useState(null);

  // Toast Notification
  const [toastMessage, setToastMessage] = useState(null);
  const [backendHealth, setBackendHealth] = useState({ status: "checking" });

  // 1. Initial Health & Watchlist load
  useEffect(() => {
    fetchHealth().then(setBackendHealth);
    fetchWatchlist(currentUserId).then(setWatchlist);
  }, []);

  // 2. Fetch User Recommendations when user changes
  useEffect(() => {
    setLoadingRecs(true);
    fetchUserRecommendations(currentUserId, 12)
      .then(data => {
        setRecommendations(data.recommendations || []);
        setRecMeta({
          algorithm: data.algorithm,
          timeMs: data.execution_time_ms,
          explanation: data.explanation
        });
      })
      .finally(() => setLoadingRecs(false));

    // Reload watchlist for switched user
    fetchWatchlist(currentUserId).then(setWatchlist);
  }, [currentUserId]);

  // 3. Fetch Catalog Movies when genre or search query changes
  useEffect(() => {
    setLoadingCatalog(true);
    const timeout = setTimeout(() => {
      fetchMovies({
        genre: selectedGenre,
        search: searchQuery,
        limit: 24
      })
        .then(data => setCatalogMovies(data || []))
        .finally(() => setLoadingCatalog(false));
    }, 250);

    return () => clearTimeout(timeout);
  }, [selectedGenre, searchQuery]);

  // Watchlist toggle handler
  const handleToggleWatchlist = async (movie) => {
    const exists = watchlist.some(m => m.movie_id === movie.movie_id);
    if (exists) {
      setWatchlist(prev => prev.filter(m => m.movie_id !== movie.movie_id));
      await removeFromWatchlist(currentUserId, movie.movie_id);
      showToast(`Removed "${movie.title}" from Watchlist`);
    } else {
      setWatchlist(prev => [movie, ...prev]);
      await addToWatchlist(currentUserId, movie.movie_id);
      showToast(`Added "${movie.title}" to Watchlist!`);
    }
  };

  // Rating submitted handler
  const handleRatingSubmitted = ({ movie, rating, cacheInvalidated }) => {
    showToast(
      `★ ${rating.toFixed(1)} recorded for "${movie.title}". Redis cache invalidated!`,
      "success"
    );
    // Refresh user recommendations to reflect invalidated cache
    fetchUserRecommendations(currentUserId, 12).then(data => {
      setRecommendations(data.recommendations || []);
      setRecMeta({
        algorithm: data.algorithm,
        timeMs: data.execution_time_ms,
        explanation: "Refreshed from PySpark ALS Matrix Factorization"
      });
    });
  };

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage(null);
    }, 4000);
  };

  const isInWatchlist = (movieId) => watchlist.some(m => m.movie_id === movieId);

  return (
    <div className="min-h-screen flex flex-col bg-slate-950 text-slate-100 selection:bg-rose-500 selection:text-white">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 animate-in slide-in-from-bottom-5 fade-in duration-300">
          <div className="flex items-center gap-2.5 px-4 py-3 rounded-2xl bg-slate-900 border border-rose-500/40 text-white text-xs font-medium shadow-2xl shadow-rose-950/80 backdrop-blur-md">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
            <span>{toastMessage}</span>
          </div>
        </div>
      )}

      {/* Navigation */}
      <Navbar
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
        currentUserId={currentUserId}
        onSelectUser={setCurrentUserId}
        watchlistCount={watchlist.length}
        onOpenWatchlist={() => setIsWatchlistOpen(true)}
        onOpenPredictor={() => setIsPredictorOpen(true)}
        backendStatus={backendHealth.status}
      />

      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full">
        {/* Hero Section */}
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-slate-900 via-rose-950/30 to-slate-900 border border-slate-800 p-8 sm:p-12 mb-10 shadow-2xl">
          <div className="relative z-10 max-w-3xl">
            <div className="flex flex-wrap items-center gap-2 mb-4">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs font-semibold uppercase tracking-wider">
                <Sparkles className="w-3.5 h-3.5" /> Apache Spark MLlib ALS Matrix Factorization
              </span>
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs font-semibold uppercase tracking-wider">
                <Database className="w-3.5 h-3.5" /> MovieLens 100K Dataset
              </span>
            </div>

            <h1 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight leading-tight mb-4">
              AI-Powered Cluster <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-rose-400 via-pink-400 to-amber-300">
                Movie Recommendation System
              </span>
            </h1>

            <p className="text-xs sm:text-sm text-slate-300 mb-6 leading-relaxed max-w-2xl">
              CineMatch decomposes high-dimensional sparse user-item interaction matrices using <strong>Alternating Least Squares (ALS)</strong> on PySpark, delivering real-time microsecond latent vector inference and personalized collaborative filtering.
            </p>

            <div className="flex flex-wrap items-center gap-3">
              <button
                onClick={() => setIsPredictorOpen(true)}
                className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-rose-600 to-amber-600 hover:from-rose-500 hover:to-amber-500 text-white font-medium text-xs transition-all shadow-lg shadow-rose-950/50 flex items-center gap-2"
              >
                <Zap className="w-4 h-4" />
                Live Online Predictor
              </button>
              <button
                onClick={() => setIsWatchlistOpen(true)}
                className="px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium text-xs transition-colors border border-slate-700"
              >
                View Watchlist ({watchlist.length})
              </button>
            </div>
          </div>
        </div>

        {/* SECTION 1: Personalized Top-N Recommendations */}
        <div className="mb-12">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
            <div className="flex items-center gap-2.5">
              <div className="w-2 h-6 bg-gradient-to-b from-rose-500 to-amber-500 rounded-full" />
              <div>
                <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
                  Recommended For User #{currentUserId}
                  <span className="text-xs font-normal text-rose-400 bg-rose-500/10 px-2 py-0.5 rounded-full border border-rose-500/20">
                    ALS Factorization
                  </span>
                </h2>
              </div>
            </div>

            {/* Performance Metric Pill */}
            {recMeta && (
              <div className="flex items-center gap-3 text-xs text-slate-400 bg-slate-900 px-3.5 py-1.5 rounded-full border border-slate-800">
                <span className="flex items-center gap-1 text-emerald-400 font-semibold">
                  <Zap className="w-3.5 h-3.5" /> {recMeta.timeMs}ms Latency
                </span>
                <span className="hidden sm:inline border-l border-slate-800 pl-3">
                  {recMeta.explanation}
                </span>
              </div>
            )}
          </div>

          {loadingRecs ? (
            <div className="py-20 text-center flex flex-col items-center">
              <div className="w-8 h-8 border-2 border-rose-500 border-t-transparent rounded-full animate-spin mb-3" />
              <p className="text-xs text-slate-400">Loading personalized ALS recommendations...</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4 sm:gap-6">
              {recommendations.map(movie => (
                <MovieCard
                  key={movie.movie_id}
                  movie={movie}
                  onRate={setRatingMovie}
                  onSimilar={setSimilarMovie}
                  onToggleWatchlist={handleToggleWatchlist}
                  onOpenDetail={setDetailMovie}
                  isInWatchlist={isInWatchlist(movie.movie_id)}
                />
              ))}
            </div>
          )}
        </div>

        {/* SECTION 2: Full Catalog Browsing with Search & Genre Filter */}
        <div className="mb-12">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
            <div className="flex items-center gap-2.5">
              <div className="w-2 h-6 bg-slate-700 rounded-full" />
              <h2 className="text-xl font-bold text-white tracking-tight">
                Explore MovieLens Catalog (1,682 Titles)
              </h2>
            </div>

            {/* Genre Filter Pills */}
            <div className="flex items-center gap-1.5 overflow-x-auto pb-2 scrollbar-none max-w-full sm:max-w-xl">
              {GENRES.map(genre => (
                <button
                  key={genre}
                  onClick={() => setSelectedGenre(genre)}
                  className={`px-3 py-1 rounded-full text-xs font-medium whitespace-nowrap transition-all ${
                    selectedGenre === genre
                      ? "bg-rose-600 text-white shadow-md shadow-rose-950/50"
                      : "bg-slate-900 text-slate-400 hover:text-white hover:bg-slate-800 border border-slate-800"
                  }`}
                >
                  {genre}
                </button>
              ))}
            </div>
          </div>

          {loadingCatalog ? (
            <div className="py-20 text-center flex flex-col items-center">
              <div className="w-8 h-8 border-2 border-slate-600 border-t-transparent rounded-full animate-spin mb-3" />
              <p className="text-xs text-slate-400">Filtering catalog...</p>
            </div>
          ) : catalogMovies.length === 0 ? (
            <div className="py-20 text-center text-sm text-slate-500 bg-slate-900/40 rounded-3xl border border-slate-800/80">
              No movies match your search or genre filter.
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4 sm:gap-6">
              {catalogMovies.map(movie => (
                <MovieCard
                  key={movie.movie_id}
                  movie={movie}
                  onRate={setRatingMovie}
                  onSimilar={setSimilarMovie}
                  onToggleWatchlist={handleToggleWatchlist}
                  onOpenDetail={setDetailMovie}
                  isInWatchlist={isInWatchlist(movie.movie_id)}
                />
              ))}
            </div>
          )}
        </div>
      </main>

      <Footer />

      {/* Movie Detail Modal */}
      {detailMovie && (
        <MovieDetailModal
          movie={detailMovie}
          isInWatchlist={isInWatchlist(detailMovie.movie_id)}
          onClose={() => setDetailMovie(null)}
          onRate={(m) => { setDetailMovie(null); setRatingMovie(m); }}
          onSimilar={(m) => { setDetailMovie(null); setSimilarMovie(m); }}
          onToggleWatchlist={(m) => handleToggleWatchlist(m)}
        />
      )}

      {/* Interactive Modals */}
      <RatingModal
        movie={ratingMovie}
        userId={currentUserId}
        onClose={() => setRatingMovie(null)}
        onRatingSubmitted={handleRatingSubmitted}
      />

      <SimilarMoviesModal
        movie={similarMovie}
        onClose={() => setSimilarMovie(null)}
        onSelectMovie={(m) => {
          setSimilarMovie(m);
        }}
      />

      {isPredictorOpen && (
        <RealtimePredictorModal
          currentUserId={currentUserId}
          onClose={() => setIsPredictorOpen(false)}
        />
      )}

      <WatchlistDrawer
        isOpen={isWatchlistOpen}
        onClose={() => setIsWatchlistOpen(false)}
        watchlist={watchlist}
        onRemoveFromWatchlist={(id) => {
          setWatchlist(prev => prev.filter(m => m.movie_id !== id));
          removeFromWatchlist(currentUserId, id);
        }}
        onSelectMovie={(m) => {
          setIsWatchlistOpen(false);
          setSimilarMovie(m);
        }}
      />
    </div>
  );
}
