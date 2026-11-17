import React from 'react';
import { Film, Heart } from 'lucide-react';

export default function Footer() {
  return (
    <footer className="mt-20 border-t border-slate-800 bg-slate-950/80 py-10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <Film className="w-5 h-5 text-rose-500" />
          <span className="font-bold text-white text-sm">CineMatch Engine</span>
          <span className="text-xs text-slate-500">| Apache Spark MLlib & FastAPI</span>
        </div>
        <p className="text-xs text-slate-500 flex items-center gap-1">
          Built with <Heart className="w-3.5 h-3.5 text-rose-500 fill-rose-500" /> for movie enthusiasts & distributed ML systems.
        </p>
      </div>
    </footer>
  );
}
