import React, { useState } from 'react';
import { Star, X, CheckCircle, Sparkles } from 'lucide-react';
import { submitRating } from '../services/api';

export default function RatingModal({ movie, userId, onClose, onRatingSubmitted }) {
  const [rating, setRating] = useState(4.0);
  const [hoverRating, setHoverRating] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  if (!movie) return null;

  const handleSubmit = async () => {
    setIsSubmitting(true);
    try {
      const res = await submitRating(userId, movie.movie_id, rating);
      setSubmitted(true);
      setTimeout(() => {
        onRatingSubmitted({
          movie,
          rating,
          cacheInvalidated: res.cache_invalidated
        });
        onClose();
      }, 900);
    } catch (err) {
      console.error(err);
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-md bg-slate-900 border border-slate-800 rounded-3xl p-6 sm:p-8 shadow-2xl overflow-hidden">
        {/* Glow backdrop */}
        <div className="absolute -top-24 -left-24 w-48 h-48 bg-rose-500/10 rounded-full blur-3xl pointer-events-none" />

        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-5 right-5 w-8 h-8 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white flex items-center justify-center transition-colors"
        >
          <X className="w-4 h-4" />
        </button>

        {submitted ? (
          <div className="py-8 text-center flex flex-col items-center">
            <CheckCircle className="w-16 h-16 text-emerald-400 mb-4 animate-bounce" />
            <h3 className="text-xl font-bold text-white mb-2">Rating Recorded!</h3>
            <p className="text-xs text-slate-400 max-w-xs mb-3">
              Your feedback was persisted to MongoDB and triggered instant Redis cache invalidation for User #{userId}.
            </p>
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-rose-500/10 text-rose-400 text-xs font-medium">
              <Sparkles className="w-3.5 h-3.5" /> ALS Latent Vector Updated
            </span>
          </div>
        ) : (
          <div>
            <div className="flex items-center gap-2 text-xs font-semibold text-rose-400 uppercase tracking-wider mb-2">
              <Sparkles className="w-3.5 h-3.5" /> Rate & Train Engine
            </div>
            <h2 className="text-lg sm:text-xl font-bold text-white mb-1 line-clamp-1">
              {movie.title}
            </h2>
            <p className="text-xs text-slate-400 mb-6">
              User #{userId} feedback updates your personalized recommendations.
            </p>

            {/* Star Selector */}
            <div className="flex flex-col items-center justify-center py-4 bg-slate-950/50 rounded-2xl border border-slate-800/80 mb-6">
              <div className="flex items-center gap-2 mb-2">
                {[1, 2, 3, 4, 5].map((starValue) => {
                  const current = hoverRating || rating;
                  const isFilled = starValue <= current;
                  return (
                    <button
                      key={starValue}
                      type="button"
                      onMouseEnter={() => setHoverRating(starValue)}
                      onMouseLeave={() => setHoverRating(null)}
                      onClick={() => setRating(starValue)}
                      className="p-1.5 transition-transform hover:scale-125 focus:outline-none"
                    >
                      <Star
                        className={`w-8 h-8 transition-colors ${
                          isFilled
                            ? 'fill-amber-400 text-amber-400 drop-shadow-[0_0_8px_rgba(251,191,36,0.5)]'
                            : 'text-slate-600 hover:text-slate-400'
                        }`}
                      />
                    </button>
                  );
                })}
              </div>
              <span className="text-sm font-semibold text-amber-300">
                {(hoverRating || rating).toFixed(1)} Stars
              </span>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={isSubmitting}
                onClick={handleSubmit}
                className="flex-1 px-4 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-sm font-medium transition-all shadow-lg shadow-rose-950/50 disabled:opacity-50"
              >
                {isSubmitting ? "Recording..." : "Submit Rating"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
