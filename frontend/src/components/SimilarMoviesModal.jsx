import React, { useState, useEffect } from 'react';
import { X, Sparkles, Film, ArrowRight } from 'lucide-react';
import { fetchSimilarMovies } from '../services/api';

export default function SimilarMoviesModal({ movie, onClose, onSelectMovie }) {
  const [similarList, setSimilarList] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!movie) return;
    setLoading(true);
    fetchSimilarMovies(movie.movie_id, 6)
      .then(res => {
        setSimilarList(res.similar_movies || []);
      })
      .finally(() => setLoading(false));
  }, [movie]);

  if (!movie) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-3xl p-6 sm:p-8 shadow-2xl overflow-hidden max-h-[90vh] flex flex-col">
        {/* Glow */}
        <div className="absolute -top-24 -right-24 w-48 h-48 bg-amber-500/10 rounded-full blur-3xl pointer-events-none" />

        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-5 right-5 w-8 h-8 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white flex items-center justify-center transition-colors"
        >
          <X className="w-4 h-4" />
        </button>

        {/* Header */}
        <div className="mb-6">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs font-semibold uppercase tracking-wider mb-2">
            <Sparkles className="w-3.5 h-3.5" /> ALS Item Factor Cosine Similarity
          </div>
          <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
            Because you watched: <span className="text-rose-400">{movie.title}</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Latent factor vectors $\mathbf{v}_i$ factorized across 100K ratings to reveal nearest cinematic neighbors.
          </p>
        </div>

        {/* Content list */}
        <div className="flex-1 overflow-y-auto pr-1 space-y-3">
          {loading ? (
            <div className="py-12 text-center text-sm text-slate-400 flex flex-col items-center">
              <div className="w-8 h-8 border-2 border-rose-500 border-t-transparent rounded-full animate-spin mb-3" />
              Computing Cosine Distance Matrix...
            </div>
          ) : similarList.length === 0 ? (
            <div className="py-12 text-center text-sm text-slate-500">
              No latent neighbors found for this title.
            </div>
          ) : (
            similarList.map((item, idx) => (
              <div
                key={item.movie_id}
                className="group flex items-center justify-between gap-4 p-3.5 rounded-2xl bg-slate-950/50 border border-slate-800/80 hover:border-rose-500/40 hover:bg-slate-800/40 transition-all"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-10 h-14 rounded-lg bg-slate-800 overflow-hidden flex-shrink-0">
                    <img
                      src={item.poster_url || "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=500&q=80"}
                      alt={item.title}
                      className="w-full h-full object-cover group-hover:scale-110 transition-transform"
                    />
                  </div>
                  <div className="min-w-0">
                    <h4 className="text-sm font-semibold text-white group-hover:text-rose-400 transition-colors truncate">
                      {item.title}
                    </h4>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-[11px] text-slate-400">
                        {item.genres?.slice(0, 2).join(", ")}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3 flex-shrink-0">
                  <div className="text-right">
                    <span className="text-xs font-bold text-amber-400">
                      {item.predicted_rating ? `${Math.round(item.predicted_rating * 100)}% Match` : "High Match"}
                    </span>
                    <div className="text-[10px] text-slate-500">Rank #{idx + 1}</div>
                  </div>
                  {onSelectMovie && (
                    <button
                      onClick={() => {
                        onSelectMovie(item);
                        onClose();
                      }}
                      className="w-8 h-8 rounded-lg bg-slate-800 hover:bg-rose-600 text-slate-400 hover:text-white flex items-center justify-center transition-colors"
                      title="Explore this movie"
                    >
                      <ArrowRight className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="mt-6 pt-4 border-t border-slate-800 flex justify-end">
          <button
            onClick={onClose}
            className="px-5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition-colors"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
