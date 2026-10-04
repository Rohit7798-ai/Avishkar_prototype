import React from 'react';
import { useHealth } from '../../hooks/useHealth';
import { Badge } from '../ui/Badge';

export function Header({ onMenuClick }) {
  const { isHealthy, service, loading } = useHealth(true, 30000);

  return (
    <header className="h-16 bg-white border-b border-slate-200 px-4 sm:px-6 flex items-center justify-between sticky top-0 z-20">
      <div className="flex items-center gap-3">
        {/* Mobile menu toggle */}
        <button
          type="button"
          onClick={onMenuClick}
          aria-label="Toggle navigation menu"
          className="md:hidden p-2 rounded-lg text-slate-500 hover:text-slate-700 hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>

        {/* Mobile brand display */}
        <div className="flex items-center gap-2 md:hidden">
          <span className="text-xl">🌱</span>
          <span className="font-bold text-slate-900 text-sm">Farmer Decision</span>
        </div>
      </div>

      {/* Right controls: Only alert when service is disconnected to avoid distracting users */}
      <div className="flex items-center gap-3">
        {!loading && !isHealthy && (
          <Badge variant="warning" dot>
            Offline Mode
          </Badge>
        )}
      </div>
    </header>
  );
}
