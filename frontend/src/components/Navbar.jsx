import React from 'react';
import { Film, Search, Sparkles, User, Zap, Bookmark, CheckCircle2, AlertCircle } from 'lucide-react';

const USERS = [
  { id: 1, name: "User 1 (Action & Sci-Fi)", role: "Power Reviewer" },
  { id: 2, name: "User 2 (Drama & Romance)", role: "Casual Cinephile" },
  { id: 3, name: "User 3 (Animation & Kids)", role: "Family Viewer" },
  { id: 999, name: "Mentor (Demo Lead)", role: "Admin" },
];

export default function Navbar({
  searchQuery,
  setSearchQuery,
  currentUserId,
  onSelectUser,
  watchlistCount = 0,
  onOpenWatchlist,
  onOpenPredictor,
  backendStatus = "healthy"
}) {
  return (
    <header className="sticky top-0 z-40 bg-slate-900/90 backdrop-blur-md border-b border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-rose-600 to-amber-500 flex items-center justify-center shadow-lg shadow-rose-950/50">
            <Film className="w-5 h-5 text-white" />
          </div>
          <div>
            <span className="text-xl font-bold tracking-tight text-white">
              Cine<span className="text-rose-500">Match</span>
            </span>
            <span className="hidden sm:inline-block ml-2 px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wider bg-rose-500/10 text-rose-400 border border-rose-500/20 rounded-full">
              Apache Spark ALS
            </span>
          </div>
        </div>

        {/* Live Search */}
        <div className="flex-1 max-w-md hidden md:block">
          <div className="relative">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search 1,682 movies by title, genre, year..."
              className="w-full bg-slate-950 border border-slate-800 rounded-full pl-9 pr-8 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-rose-500 focus:ring-1 focus:ring-rose-500 transition-colors"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-400 hover:text-white"
              >
                ✕
              </button>
            )}
          </div>
        </div>

        {/* Right Actions */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Real-time Predictor button */}
          <button
            onClick={onOpenPredictor}
            title="Real-Time Vector Dot Product Predictor"
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-rose-300 hover:text-white bg-rose-500/10 hover:bg-rose-500 border border-rose-500/30 rounded-xl transition-all shadow-sm"
          >
            <Zap className="w-3.5 h-3.5 text-rose-400" />
            <span className="hidden sm:inline">Online Predictor</span>
          </button>

          {/* Watchlist button */}
          <button
            onClick={onOpenWatchlist}
            className="relative p-2 text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-xl transition-colors border border-slate-700/60"
            title="View Watchlist"
          >
            <Bookmark className="w-4 h-4" />
            {watchlistCount > 0 && (
              <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-rose-600 text-white text-[9px] font-bold flex items-center justify-center animate-pulse">
                {watchlistCount}
              </span>
            )}
          </button>

          {/* User selector dropdown */}
          <div className="flex items-center gap-2 pl-2 border-l border-slate-800">
            <div className="hidden lg:flex flex-col text-right">
              <span className="text-[11px] font-semibold text-white">
                User #{currentUserId}
              </span>
              <span className="text-[9px] text-slate-400">
                {USERS.find(u => u.id === currentUserId)?.role || "User"}
              </span>
            </div>

            <select
              value={currentUserId}
              onChange={(e) => onSelectUser(Number(e.target.value))}
              className="bg-slate-800 border border-slate-700 rounded-xl px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-rose-500 cursor-pointer"
            >
              {USERS.map(u => (
                <option key={u.id} value={u.id} className="bg-slate-900 text-white">
                  {u.name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>
    </header>
  );
}
