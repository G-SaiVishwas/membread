import React from 'react';
import { Command } from 'cmdk';
import { useNavigate } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import {
  HomeIcon,
  GlobeAltIcon,
  ClockIcon,
  MagnifyingGlassIcon,
  BeakerIcon,
  PuzzlePieceIcon,
  SparklesIcon,
  ArchiveBoxIcon,
  ChatBubbleLeftRightIcon,
} from '@heroicons/react/24/outline';

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
}

const pages = [
  { name: 'Dashboard', href: '/', icon: HomeIcon, keywords: 'home overview stats agents continuity score' },
  { name: 'Agent Graph', href: '/graph', icon: GlobeAltIcon, keywords: 'graph network nodes edges knowledge agent session task' },
  { name: 'Agent Time-Travel', href: '/temporal', icon: ClockIcon, keywords: 'temporal time travel bitemporal as-of search agent session cross-tool' },
  { name: 'Agent Entity History', href: '/entity-history', icon: ArchiveBoxIcon, keywords: 'entity history versions timeline evolution agent lifecycle' },
  { name: 'Agent Chat', href: '/chat', icon: ChatBubbleLeftRightIcon, keywords: 'chat conversation recall ask question agent session cross-session' },
  { name: 'Search Memories', href: '/search', icon: MagnifyingGlassIcon, keywords: 'search find query recall agent cross-tool' },
  { name: 'Timeline', href: '/timeline', icon: ClockIcon, keywords: 'timeline history events agent sessions' },
  { name: 'Playground', href: '/demo', icon: BeakerIcon, keywords: 'demo api test playground token agent sdk langgraph crewai autogen' },
  { name: 'Connectors', href: '/connectors', icon: PuzzlePieceIcon, keywords: 'connectors integrations chatgpt claude gemini cursor copilot openrouter ai tools' },
  { name: 'Plugins', href: '/plugins', icon: SparklesIcon, keywords: 'plugins claude code opencode clawdbot install terminal memory' },
];

const CommandPalette: React.FC<CommandPaletteProps> = ({ open, onClose }) => {
  const navigate = useNavigate();

  const runAction = (href: string) => {
    navigate(href);
    onClose();
  };

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/30 backdrop-blur-sm"
            onClick={onClose}
          />

          {/* Dialog */}
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: -20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: -20 }}
            transition={{ duration: 0.15 }}
            className="fixed z-50 top-[20%] left-1/2 -translate-x-1/2 w-full max-w-lg"
          >
            <Command
              label="Command palette"
              className="bg-white border border-black/10 overflow-hidden rounded-2xl shadow-2xl"
            >
              <div className="flex items-center gap-3 px-4 border-b border-black/5">
                <SparklesIcon className="w-5 h-5 text-gray-900 flex-shrink-0" />
                <Command.Input
                  placeholder="Search agents, sessions, pages..."
                  className="w-full py-4 bg-transparent text-gray-900 placeholder-gray-400 text-sm
                             focus:outline-none"
                />
              </div>

              <Command.List className="max-h-72 overflow-y-auto p-2">
                <Command.Empty className="py-8 text-center text-sm text-gray-400">
                  No results found.
                </Command.Empty>

                <Command.Group heading="Navigate" className="[&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:py-2 [&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:text-gray-400 [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-wider">
                  {pages.map((page) => (
                    <Command.Item
                      key={page.href}
                      value={`${page.name} ${page.keywords}`}
                      onSelect={() => runAction(page.href)}
                      className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-gray-600 cursor-pointer
                                 data-[selected=true]:bg-black data-[selected=true]:text-white
                                 transition-colors duration-100"
                    >
                      <page.icon className="w-4 h-4 flex-shrink-0" />
                      <span>{page.name}</span>
                    </Command.Item>
                  ))}
                </Command.Group>
              </Command.List>

              <div className="flex items-center justify-between px-4 py-2 border-t border-black/5 text-[11px] text-gray-400">
                <span>Navigate with arrow keys</span>
                <div className="flex items-center gap-2">
                  <kbd className="px-1.5 py-0.5 rounded-md bg-black/5 border border-black/10 font-mono">Enter</kbd>
                  <span>to select</span>
                  <kbd className="px-1.5 py-0.5 rounded-md bg-black/5 border border-black/10 font-mono">Esc</kbd>
                  <span>to close</span>
                </div>
              </div>
            </Command>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

export default CommandPalette;
