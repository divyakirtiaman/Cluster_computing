import React, { useState } from 'react';
import { X, Cpu, Zap, ArrowRight, Sparkles, CheckCircle2 } from 'lucide-react';
import { predictRatingRealtime } from '../services/api';

const POPULAR_TEST_MOVIES = [
  { id: 50, title: "Star Wars (1977)" },
  { id: 1, title: "Toy Story (1995)" },
  { id: 127, title: "The Godfather (1972)" },
  { id: 98, title: "Silence of the Lambs (1991)" },
  { id: 100, title: "Fargo (1996)" },
  { id: 181, title: "Return of the Jedi (1983)" },
];

export default function RealtimePredictorModal({ currentUserId, onClose }) {
  const [userId, setUserId] = useState(currentUserId || 1);
  const [movieId, setMovieId] = useState(50);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleCompute = async () => {
    setLoading(true);
    try {
      const res = await predictRatingRealtime(userId, movieId);
      setResult(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-lg bg-slate-900 border border-slate-800 rounded-3xl p-6 sm:p-8 shadow-2xl overflow-hidden">
        {/* Glow */}
        <div className="absolute -top-24 -left-24 w-48 h-48 bg-rose-500/15 rounded-full blur-3xl pointer-events-none" />

        <button
          onClick={onClose}
          className="absolute top-5 right-5 w-8 h-8 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white flex items-center justify-center transition-colors"
        >
          <X className="w-4 h-4" />
        </button>

        <div className="mb-6">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs font-semibold uppercase tracking-wider mb-2">
            <Zap className="w-3.5 h-3.5" /> Online Microsecond Inference
          </div>
          <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
            Real-Time Rating Predictor
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Computes $\hat{r}_{ui} = \mathbf{u}_u^T \cdot \mathbf{v}_i$ online using pre-factorized 20-dimensional ALS latent vectors.
          </p>
        </div>

        {/* Inputs */}
        <div className="space-y-4 mb-6">
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
              User ID (1 to 943)
            </label>
            <input
              type="number"
              min="1"
              max="943"
              value={userId}
              onChange={(e) => setUserId(Math.max(1, Math.min(943, Number(e.target.value))))}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-rose-500 focus:ring-1 focus:ring-rose-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
              Target Movie ID
            </label>
            <div className="flex gap-2 mb-2">
              <input
                type="number"
                min="1"
                max="1682"
                value={movieId}
                onChange={(e) => setMovieId(Number(e.target.value))}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-rose-500 focus:ring-1 focus:ring-rose-500"
              />
            </div>
            {/* Quick picker */}
            <div className="flex flex-wrap gap-1.5">
              {POPULAR_TEST_MOVIES.map(m => (
                <button
                  key={m.id}
                  onClick={() => setMovieId(m.id)}
                  className={`text-[10px] px-2 py-1 rounded-lg border transition-all ${
                    movieId === m.id
                      ? "bg-rose-500/20 text-rose-300 border-rose-500/40"
                      : "bg-slate-950 text-slate-400 border-slate-800 hover:text-white"
                  }`}
                >
                  {m.title}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Compute Button */}
        <button
          onClick={handleCompute}
          disabled={loading}
          className="w-full py-3 rounded-xl bg-gradient-to-r from-rose-600 to-amber-600 hover:from-rose-500 hover:to-amber-500 text-white font-semibold text-sm transition-all shadow-lg shadow-rose-950/50 flex items-center justify-center gap-2 mb-6 disabled:opacity-50"
        >
          {loading ? (
            <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : (
            <>
              <Cpu className="w-4 h-4" />
              Compute Vector Dot Product
            </>
          )}
        </button>

        {/* Result Card */}
        {result && (
          <div className="p-4 rounded-2xl bg-slate-950/70 border border-slate-800 animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs text-slate-400">Predicted Affinity Rating:</span>
              <span className="text-2xl font-black text-transparent bg-clip-text bg-gradient-to-r from-rose-400 to-amber-300">
                ★ {result.predicted_rating} / 5.0
              </span>
            </div>
            <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-400 border-t border-slate-800/80 pt-3">
              <div>
                <span className="text-slate-500">Latency:</span> &lt; 0.5ms (In-Memory)
              </div>
              <div>
                <span className="text-slate-500">Algorithm:</span> Spark ALS Latent
              </div>
              <div>
                <span className="text-slate-500">Vector Rank:</span> k = 20 dimensions
              </div>
              <div className="flex items-center gap-1 text-emerald-400">
                <CheckCircle2 className="w-3 h-3" /> Clamped [1.0, 5.0]
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
