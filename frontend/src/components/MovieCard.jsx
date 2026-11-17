import React from 'react';
import { Star, Sparkles, Plus, Check, Compass } from 'lucide-react';

export default function MovieCard({
  movie,
  onRate,
  onSimilar,
  onToggleWatchlist,
  onOpenDetail,
  isInWatchlist = false
}) {
  return (
    <div
      className="group relative bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden hover:border-slate-700 transition-all duration-300 hover:shadow-2xl hover:shadow-rose-950/30 hover:-translate-y-1 flex flex-col cursor-pointer"
      onClick={() => onOpenDetail && onOpenDetail(movie)}
    >
      {/* Poster Container */}
      <div className="relative aspect-[2/3] w-full overflow-hidden bg-slate-950">
        <img
          src={movie.poster_url || "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=500&q=80"}
          alt={movie.title}
          className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
          loading="lazy"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/20 to-transparent opacity-90 group-hover:opacity-80 transition-opacity" />

        {/* Rating Match Badge */}
        {movie.predicted_rating ? (
          <div className="absolute top-2.5 right-2.5 flex items-center gap-1 px-2 py-0.5 rounded-full bg-slate-900/90 backdrop-blur-md border border-rose-500/40 text-rose-300 text-[11px] font-semibold shadow-md">
            <Sparkles className="w-3 h-3 text-rose-400" />
            <span>{typeof movie.predicted_rating === 'number' ? movie.predicted_rating.toFixed(2) : movie.predicted_rating}</span>
          </div>
        ) : movie.average_rating ? (
          <div className="absolute top-2.5 right-2.5 flex items-center gap-1 px-2 py-0.5 rounded-full bg-slate-900/90 backdrop-blur-md border border-amber-500/40 text-amber-300 text-[11px] font-semibold shadow-md">
            <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
            <span>{movie.average_rating.toFixed(1)}</span>
          </div>
        ) : null}

        {/* Hover Action Overlay */}
        <div className="absolute inset-x-0 bottom-2 px-2.5 opacity-0 group-hover:opacity-100 transition-all duration-300 transform translate-y-2 group-hover:translate-y-0 flex items-center justify-between gap-1.5">
          {onSimilar && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onSimilar(movie);
              }}
              title="Find Similar (ALS Cosine Distance)"
              className="flex-1 py-1 px-2 rounded-lg bg-slate-900/90 hover:bg-rose-600 text-[10px] font-medium text-white backdrop-blur-sm border border-slate-700/60 flex items-center justify-center gap-1 transition-colors shadow-lg"
            >
              <Compass className="w-3 h-3 text-rose-300" />
              <span>Similar</span>
            </button>
          )}

          {onRate && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onRate(movie);
              }}
              title="Rate this movie"
              className="py-1 px-2 rounded-lg bg-slate-900/90 hover:bg-amber-500 hover:text-slate-950 text-[10px] font-medium text-amber-300 backdrop-blur-sm border border-amber-500/30 flex items-center justify-center gap-1 transition-colors shadow-lg"
            >
              <Star className="w-3 h-3 fill-amber-400" />
              <span>Rate</span>
            </button>
          )}
        </div>
      </div>

      {/* Card Info */}
      <div className="p-3.5 flex-1 flex flex-col justify-between">
        <div>
          <h3 className="font-semibold text-white text-xs sm:text-sm line-clamp-1 group-hover:text-rose-400 transition-colors" title={movie.title}>
            {movie.title}
          </h3>
          <div className="flex flex-wrap gap-1 mt-1.5">
            {movie.genres?.slice(0, 2).map((genre, idx) => (
              <span
                key={idx}
                className="px-1.5 py-0.5 text-[9px] font-medium rounded bg-slate-800 text-slate-300 border border-slate-700/40"
              >
                {genre}
              </span>
            ))}
          </div>
        </div>

        {/* Bottom Actions */}
        <div className="mt-3 pt-2.5 border-t border-slate-800/80 flex items-center justify-between text-[10px] text-slate-500">
          <span>ID #{movie.movie_id}</span>
          <button
            onClick={(e) => {
              e.stopPropagation();
              if (onToggleWatchlist) onToggleWatchlist(movie);
            }}
            title={isInWatchlist ? "Remove from Watchlist" : "Add to Watchlist"}
            className={`w-6 h-6 rounded-md flex items-center justify-center transition-all ${
              isInWatchlist
                ? "bg-rose-500 text-white shadow-md shadow-rose-950/50"
                : "bg-slate-800 hover:bg-rose-600 text-slate-300 hover:text-white"
            }`}
          >
            {isInWatchlist ? <Check className="w-3 h-3" /> : <Plus className="w-3 h-3" />}
          </button>
        </div>
      </div>
    </div>
  );
}
