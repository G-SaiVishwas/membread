import React from 'react';
import { useLocation, Link } from 'react-router-dom';
import {
  SparklesIcon,
  MagnifyingGlassIcon,
  CommandLineIcon,
  BookOpenIcon,
  ChevronRightIcon,
} from '@heroicons/react/24/outline';

const pageNames: Record<string, string> = {
  '/': 'Overview',
  '/graph': 'Agent Graph',
  '/timeline': 'Timeline',
  '/search': 'Search',
  '/temporal': 'Agent Time-Travel',
  '/entity-history': 'Agent Entity History',
  '/chat': 'Agent Chat',
  '/connectors': 'Connectors',
  '/plugins': 'Plugins',
  '/docs': 'Documentation',
};

interface HeaderProps {
  onOpenCommandPalette?: () => void;
  apiOk?: boolean;
}

const Header: React.FC<HeaderProps> = ({ onOpenCommandPalette, apiOk = true }) => {
  const location = useLocation();
  const currentPage = pageNames[location.pathname] || 'Page';

  return (
    <header className="sticky top-0 z-40 px-4 pt-3 pb-0">
      <nav className="flex items-center justify-between px-5 h-[52px] bg-white/70 backdrop-blur-2xl border border-black/[0.06] rounded-2xl shadow-[0_1px_12px_rgba(0,0,0,0.04),0_0_0_1px_rgba(0,0,0,0.02)]">

        {/* ── Left: Logo + Breadcrumb ── */}
        <div className="flex items-center gap-4 min-w-0">
          <div className="flex items-center gap-2.5 shrink-0">
            <div className="w-8 h-8 rounded-[10px] bg-black flex items-center justify-center shadow-[0_2px_8px_rgba(0,0,0,0.12)]">
              <SparklesIcon className="w-4 h-4 text-white" />
            </div>
            <div className="flex flex-col leading-none">
              <span className="text-[14px] font-extrabold text-gray-900 tracking-tight">
                membread
              </span>
              <span className="text-[9px] font-semibold text-gray-400 tracking-[0.12em] uppercase mt-[1px]">
                memory layer
              </span>
            </div>
          </div>

          {/* Breadcrumb separator */}
          <div className="flex items-center gap-2 text-gray-300">
            <ChevronRightIcon className="w-3 h-3 stroke-[2.5]" />
            <span className="text-[13px] font-medium text-gray-500 truncate">
              {currentPage}
            </span>
          </div>
        </div>

        {/* ── Center: Search ── */}
        <button
          onClick={onOpenCommandPalette}
          className="group flex items-center gap-3 px-4 py-2 w-[360px] max-w-[420px] bg-gray-50 border border-gray-200/80 rounded-xl text-sm text-gray-400 hover:bg-gray-100/80 hover:border-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-900/10 focus:border-gray-300 transition-all duration-200"
        >
          <MagnifyingGlassIcon className="w-[18px] h-[18px] text-gray-400 group-hover:text-gray-500 transition-colors shrink-0" />
          <span className="flex-1 text-left text-[13px] text-gray-400">Search memories, agents, sessions…</span>
          <kbd className="hidden sm:flex items-center gap-0.5 px-2 py-1 bg-white rounded-lg text-[10px] font-mono text-gray-400 border border-gray-200 shadow-sm">
            <CommandLineIcon className="w-3 h-3" />K
          </kbd>
        </button>

        {/* ── Right: Status + Docs ── */}
        <div className="flex items-center gap-1.5 shrink-0">
          {/* API Status dot */}
          <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg">
            <div className={`w-[7px] h-[7px] rounded-full ${apiOk ? 'bg-emerald-500 shadow-[0_0_6px_rgba(16,185,129,0.4)]' : 'bg-red-500 shadow-[0_0_6px_rgba(239,68,68,0.4)]'}`} />
          </div>

          {/* Docs */}
          <Link
            to="/docs"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-gray-500 hover:text-gray-700 hover:bg-black/[0.04] transition-all duration-150"
          >
            <BookOpenIcon className="w-[18px] h-[18px] stroke-[1.6]" />
            <span className="text-[12px] font-medium hidden sm:inline">Docs</span>
          </Link>
        </div>
      </nav>
    </header>
  );
};

export default Header;