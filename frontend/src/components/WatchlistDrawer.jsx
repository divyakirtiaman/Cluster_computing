import React from 'react';
import { X, Trash2, Film, Star, ExternalLink } from 'lucide-react';

export default function WatchlistDrawer({
  isOpen,
  onClose,
  watchlist,
  onRemoveFromWatchlist,
  onSelectMovie
}) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-slate-950/70 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="absolute inset-y-0 right-0 max-w-full flex pl-10">
        <div className="w-screen max-w-md bg-slate-900 border-l border-slate-800 shadow-2xl flex flex-col">
          {/* Header */}
          <div className="p-6 border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-rose-500/20 text-rose-400 flex items-center justify-center font-bold">
                <Film className="w-4 h-4" />
              </div>
              <div>
                <h2 className="text-base font-bold text-white">Your Watchlist</h2>
                <p className="text-xs text-slate-400">{watchlist.length} saved movies</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white flex items-center justify-center transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* List */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {watchlist.length === 0 ? (
              <div className="py-20 text-center flex flex-col items-center">
                <Film className="w-12 h-12 text-slate-700 mb-3" />
                <h4 className="text-sm font-semibold text-slate-300 mb-1">Your watchlist is empty</h4>
                <p className="text-xs text-slate-500 max-w-xs">
                  Click the plus (+) icon on any movie card in the catalog or recommendations to save it here.
                </p>
              </div>
            ) : (
              watchlist.map((movie) => (
                <div
                  key={movie.movie_id}
                  className="group flex items-center justify-between gap-3 p-3 rounded-2xl bg-slate-950/60 border border-slate-800/80 hover:border-slate-700 transition-all"
                >
                  <div
                    onClick={() => {
                      if (onSelectMovie) onSelectMovie(movie);
                    }}
                    className="flex items-center gap-3 min-w-0 cursor-pointer flex-1"
                  >
                    <div className="w-12 h-16 rounded-xl bg-slate-800 overflow-hidden flex-shrink-0">
                      <img
                        src={movie.poster_url || "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=500&q=80"}
                        alt={movie.title}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                      />
                    </div>
                    <div className="min-w-0">
                      <h4 className="text-xs sm:text-sm font-semibold text-white group-hover:text-rose-400 transition-colors truncate">
                        {movie.title}
                      </h4>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-[10px] text-slate-400 truncate">
                          {movie.genres?.slice(0, 2).join(", ")}
                        </span>
                      </div>
                      {movie.predicted_rating && (
                        <div className="flex items-center gap-1 text-[11px] text-rose-400 font-semibold mt-1">
                          <Star className="w-3 h-3 fill-rose-400" />
                          <span>{movie.predicted_rating} Match</span>
                        </div>
                      )}
                    </div>
                  </div>

                  <button
                    onClick={() => onRemoveFromWatchlist(movie.movie_id)}
                    className="p-2 text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-colors"
                    title="Remove from Watchlist"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))
            )}
          </div>

          {/* Footer */}
          <div className="p-6 border-t border-slate-800">
            <button
              onClick={onClose}
              className="w-full py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
