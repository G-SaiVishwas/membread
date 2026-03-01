import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import clsx from 'clsx';
import {
  HomeIcon,
  ShareIcon,
  MagnifyingGlassIcon,
  ChartBarIcon,
  PuzzlePieceIcon,
  GlobeAltIcon,
  CommandLineIcon,
  ClockIcon,
  ArchiveBoxIcon,
  ChatBubbleLeftRightIcon,
} from '@heroicons/react/24/outline';

interface DockItem {
  name: string;
  href: string;
  icon: React.FC<{ className?: string }>;
}

const primaryItems: DockItem[] = [
  { name: 'Overview', href: '/', icon: HomeIcon },
  { name: 'Agent Graph', href: '/graph', icon: ShareIcon },
  { name: 'Search', href: '/search', icon: MagnifyingGlassIcon },
  { name: 'Time Travel', href: '/temporal', icon: ClockIcon },
  { name: 'Entity History', href: '/entity-history', icon: ArchiveBoxIcon },
  { name: 'Agent Chat', href: '/chat', icon: ChatBubbleLeftRightIcon },
  { name: 'Timeline', href: '/timeline', icon: ChartBarIcon },
];

const utilityItems: DockItem[] = [
  { name: 'Connectors', href: '/connectors', icon: GlobeAltIcon },
  { name: 'Plugins', href: '/plugins', icon: CommandLineIcon },
];

const DockIcon: React.FC<{ item: DockItem; active: boolean }> = ({ item, active }) => {
  const [hovered, setHovered] = useState(false);

  return (
    <Link
      to={item.href}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      className="relative flex flex-col items-center group"
    >
      {/* Tooltip */}
      <div
        className={clsx(
          'absolute -top-10 px-3 py-1.5 rounded-xl text-xs font-medium whitespace-nowrap transition-all duration-200 pointer-events-none',
          'bg-black text-white shadow-lg',
          hovered ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-2'
        )}
      >
        {item.name}
      </div>

      {/* Icon button */}
      <div
        className={clsx(
          'w-12 h-12 flex items-center justify-center rounded-2xl transition-all duration-200 cursor-pointer',
          active
            ? 'bg-white/20 text-white'
            : 'text-white/50 hover:text-white hover:bg-white/10',
          hovered && 'scale-125'
        )}
      >
        <item.icon className="w-[22px] h-[22px] stroke-[1.5]" />
      </div>

      {/* Active dot */}
      <div
        className={clsx(
          'w-1 h-1 rounded-full mt-0.5 transition-all duration-200',
          active ? 'bg-white' : 'bg-transparent'
        )}
      />
    </Link>
  );
};

const Dock: React.FC = () => {
  const location = useLocation();

  const isActive = (href: string) =>
    href === '/' ? location.pathname === '/' : location.pathname.startsWith(href);

  return (
    <div className="fixed bottom-5 left-1/2 -translate-x-1/2 z-50">
      <nav className="flex items-center gap-1 px-5 py-3 bg-black rounded-[20px] shadow-[0_8px_40px_rgba(0,0,0,0.25)]">
        {/* Primary nav items */}
        {primaryItems.map((item) => (
          <DockIcon key={item.href} item={item} active={isActive(item.href)} />
        ))}

        {/* Separator */}
        <div className="w-px h-8 bg-white/15 mx-2" />

        {/* Utility items */}
        {utilityItems.map((item) => (
          <DockIcon key={item.href} item={item} active={isActive(item.href)} />
        ))}
      </nav>
    </div>
  );
};

export default Dock;
