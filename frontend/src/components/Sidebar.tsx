import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import clsx from 'clsx';
import {
  HomeIcon,
  TagIcon,
  ShareIcon,
  ChartBarIcon,
  PuzzlePieceIcon,
  ArrowUpTrayIcon,
  KeyIcon,
  CubeIcon,
  UsersIcon,
  CreditCardIcon,
  Cog6ToothIcon,
  MagnifyingGlassIcon,
  CommandLineIcon,
  SparklesIcon,
  ChevronRightIcon,
} from '@heroicons/react/24/outline';

interface NavItem {
  name: string;
  href: string;
  icon: React.FC<{ className?: string }>;
}

interface NavGroup {
  label?: string;
  items: NavItem[];
}

const navGroups: NavGroup[] = [
  {
    items: [
      { name: 'Overview', href: '/', icon: HomeIcon },
      { name: 'Container Tags', href: '/tags', icon: TagIcon },
      { name: 'Memory Graph', href: '/graph', icon: ShareIcon },
      { name: 'Requests', href: '/requests', icon: ChartBarIcon },
    ],
  },
  {
    label: 'DATA',
    items: [
      { name: 'Connectors', href: '/connectors', icon: PuzzlePieceIcon },
      { name: 'Import', href: '/import', icon: ArrowUpTrayIcon },
    ],
  },
  {
    label: 'DEVELOPER',
    items: [
      { name: 'API Keys', href: '/keys', icon: KeyIcon },
      { name: 'Plugins', href: '/plugins', icon: CubeIcon },
    ],
  },
  {
    label: 'ORGANIZATION',
    items: [
      { name: 'Team', href: '/team', icon: UsersIcon },
      { name: 'Billing', href: '/billing', icon: CreditCardIcon },
      { name: 'Settings', href: '/settings', icon: Cog6ToothIcon },
    ],
  },
];

interface SidebarProps {
  onOpenCommandPalette: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({ onOpenCommandPalette }) => {
  const location = useLocation();
  const [setupDone] = useState(0);
  const setupTotal = 3;

  return (
    <nav className="w-[260px] flex-shrink-0 flex flex-col h-full bg-[#0c0f1a] border-r border-[#1e2235]">
      {/* Logo */}
      <div className="px-5 pt-5 pb-3">
        <div className="flex items-center gap-2">
          <SparklesIcon className="w-5 h-5 text-cyan-400" />
          <span className="text-[15px] font-bold text-white tracking-tight">
            membread<span className="text-gray-500 text-xs align-super ml-0.5">™</span>
          </span>
        </div>
      </div>

      {/* Setup Guide */}
      <div className="mx-4 mb-3 px-3 py-2.5 bg-[#111528] rounded-lg border border-[#1e2235]">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-semibold text-gray-300">Setup Guide</span>
          <span className="text-xs text-gray-500">{setupDone}/{setupTotal}</span>
        </div>
        <div className="w-full h-1 bg-[#1a1e32] rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-cyan-400 to-blue-500 rounded-full transition-all"
            style={{ width: `${(setupDone / setupTotal) * 100}%` }}
          />
        </div>
      </div>

      {/* Search */}
      <div className="px-4 mb-3">
        <button
          onClick={onOpenCommandPalette}
          className="w-full flex items-center gap-2 px-3 py-2 bg-[#111528] border border-[#1e2235] rounded-lg text-sm text-gray-500 hover:border-[#2a3050] transition-colors"
        >
          <MagnifyingGlassIcon className="w-4 h-4" />
          <span className="flex-1 text-left">Search...</span>
          <kbd className="flex items-center gap-0.5 px-1.5 py-0.5 bg-[#0c0f1a] rounded text-[10px] font-mono text-gray-600 border border-[#1e2235]">
            <CommandLineIcon className="w-3 h-3" />K
          </kbd>
        </button>
      </div>

      {/* Navigation */}
      <div className="flex-1 overflow-y-auto px-3 space-y-1">
        {navGroups.map((group, gi) => (
          <div key={gi} className={gi > 0 ? 'pt-4' : ''}>
            {group.label && (
              <p className="px-3 mb-2 text-[10px] font-semibold tracking-[0.1em] text-gray-600 uppercase">
                {group.label}
              </p>
            )}
            {group.items.map((item) => {
              const active = item.href === '/'
                ? location.pathname === '/'
                : location.pathname.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  to={item.href}
                  className={clsx(
                    'group relative flex items-center gap-3 px-3 py-2 rounded-md text-[13px] font-medium transition-all duration-150',
                    active
                      ? 'bg-[#151929] text-white'
                      : 'text-gray-500 hover:text-gray-300 hover:bg-[#111528]'
                  )}
                >
                  {active && (
                    <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 bg-cyan-400 rounded-r-full" />
                  )}
                  <item.icon className={clsx('w-[18px] h-[18px] flex-shrink-0', active ? 'text-gray-300' : 'text-gray-600 group-hover:text-gray-400')} />
                  <span>{item.name}</span>
                  {item.name === 'Settings' && (
                    <ChevronRightIcon className="w-3.5 h-3.5 ml-auto text-gray-600" />
                  )}
                </Link>
              );
            })}
          </div>
        ))}
      </div>
    </nav>
  );
};

export default Sidebar;