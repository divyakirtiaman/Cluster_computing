import React, { useEffect } from 'react';
import {
  X, Star, Sparkles, Compass, Plus, Check,
  ExternalLink, Film, Calendar, Hash
} from 'lucide-react';

export default function MovieDetailModal({
  movie,
  isInWatchlist = false,
  onClose,
  onRate,
  onSimilar,
  onToggleWatchlist
}) {
  // Close on Escape key
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  if (!movie) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" />

      {/* Modal Panel */}
      <div
        className="relative z-10 w-full max-w-2xl bg-slate-900 border border-slate-700 rounded-2xl overflow-hidden shadow-2xl shadow-black/60"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Hero Poster + Gradient */}
        <div className="relative h-64 sm:h-72 overflow-hidden">
          <img
            src={movie.poster_url || "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=800&q=80"}
            alt={movie.title}
            className="w-full h-full object-cover"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-slate-900 via-slate-900/50 to-transparent" />

          {/* Close Button */}
          <button
            onClick={onClose}
            className="absolute top-3 right-3 w-8 h-8 rounded-full bg-black/50 hover:bg-black/80 flex items-center justify-center text-white transition-colors backdrop-blur-sm"
          >
            <X className="w-4 h-4" />
          </button>

          {/* Rating Badge */}
          <div className="absolute top-3 left-3">
            {movie.predicted_rating ? (
              <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-900/90 backdrop-blur-md border border-rose-500/40 text-rose-300 text-sm font-semibold">
                <Sparkles className="w-3.5 h-3.5 text-rose-400" />
                <span>{typeof movie.predicted_rating === 'number' ? movie.predicted_rating.toFixed(2) : movie.predicted_rating} predicted</span>
              </div>
            ) : movie.average_rating ? (
              <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-900/90 backdrop-blur-md border border-amber-500/40 text-amber-300 text-sm font-semibold">
                <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
                <span>{movie.average_rating.toFixed(1)} avg rating</span>
              </div>
            ) : null}
          </div>

          {/* Title at bottom of hero */}
          <div className="absolute bottom-0 left-0 right-0 p-5">
            <h2 className="text-xl sm:text-2xl font-bold text-white leading-tight">{movie.title}</h2>
          </div>
        </div>

        {/* Body */}
        <div className="p-5 space-y-4">
          {/* Metadata Row */}
          <div className="flex flex-wrap gap-3 text-sm text-slate-400">
            {movie.movie_id && (
              <span className="flex items-center gap-1.5">
                <Hash className="w-3.5 h-3.5" />
                Movie ID {movie.movie_id}
              </span>
            )}
            {movie.release_date && (
              <span className="flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5" />
                {movie.release_date}
              </span>
            )}
            {movie.rating_count && (
              <span className="flex items-center gap-1.5">
                <Film className="w-3.5 h-3.5" />
                {movie.rating_count.toLocaleString()} ratings
              </span>
            )}
          </div>

          {/* Genres */}
          {movie.genres?.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {movie.genres.map((genre, i) => (
                <span
                  key={i}
                  className="px-2.5 py-1 text-xs font-medium rounded-lg bg-slate-800 text-slate-300 border border-slate-700"
                >
                  {genre}
                </span>
              ))}
            </div>
          )}

          {/* IMDb Link */}
          {movie.imdb_url && (
            <a
              href={movie.imdb_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-sm text-amber-400 hover:text-amber-300 transition-colors"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              View on IMDb
            </a>
          )}

          {/* Divider */}
          <div className="border-t border-slate-800" />

          {/* Action Buttons */}
          <div className="flex flex-wrap gap-3">
            {onRate && (
              <button
                onClick={() => { onRate(movie); onClose(); }}
                className="flex-1 min-w-[120px] flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold text-sm transition-colors"
              >
                <Star className="w-4 h-4 fill-current" />
                Rate Movie
              </button>
            )}

            {onSimilar && (
              <button
                onClick={() => { onSimilar(movie); onClose(); }}
                className="flex-1 min-w-[120px] flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-semibold text-sm transition-colors"
              >
                <Compass className="w-4 h-4" />
                Find Similar
              </button>
            )}

            {onToggleWatchlist && (
              <button
                onClick={() => { onToggleWatchlist(movie); }}
                className={`flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl font-semibold text-sm transition-all border ${
                  isInWatchlist
                    ? 'bg-rose-500/20 border-rose-500/50 text-rose-300 hover:bg-rose-500/30'
                    : 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700'
                }`}
              >
                {isInWatchlist ? (
                  <><Check className="w-4 h-4" /> In Watchlist</>
                ) : (
                  <><Plus className="w-4 h-4" /> Add to Watchlist</>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
