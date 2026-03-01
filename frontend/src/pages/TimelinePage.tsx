import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { useApi } from '../api/client';
import { useAuth } from '../context/AuthContext';
import EmptyState from '../components/EmptyState';
import {
  ClockIcon,
  HashtagIcon,
  ChevronDownIcon,
  ChevronUpIcon,
} from '@heroicons/react/24/outline';

interface Item {
  id: string;
  text: string;
  metadata: any;
}

const TimelinePage: React.FC = () => {
  const { token } = useAuth();
  const api = useApi();
  const [items, setItems] = useState<Item[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!token) return;
    (async () => {
      try {
        const resp = await api.get('/api/memory/list', {
          headers: { Authorization: `Bearer ${token}` },
        });
        setItems(resp.data.items);
      } catch (e: any) {
        setError(e.message);
      }
    })();
  }, [token]);

  const toggle = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  if (!token) {
    return (
      <EmptyState
        icon={ClockIcon}
        title="Timeline"
        description="Authenticate to view your memory timeline."
        action={{ label: 'Go to Playground', onClick: () => window.location.href = '/demo' }}
      />
    );
  }

  if (items.length === 0 && !error) {
    return (
      <EmptyState
        icon={ClockIcon}
        title="No memories yet"
        description="Your timeline will appear here once you store observations."
        action={{ label: 'Store a Memory', onClick: () => window.location.href = '/demo' }}
      />
    );
  }

  return (
    <div className="max-w-3xl mx-auto">
      {error && (
        <div className="mb-4 p-3 glass-card border-red-200 bg-red-50 text-sm text-red-600">
          {error}
        </div>
      )}

      {/* Timeline */}
      <div className="relative">
        {/* Center line */}
        <div className="absolute left-6 top-0 bottom-0 w-px bg-gradient-to-b from-black/20 via-black/10 to-transparent" />

        <div className="space-y-4">
          {items.map((item, index) => {
            const isExpanded = expanded.has(item.id);
            const shortId = item.id.length > 12 ? `${item.id.slice(0, 6)}...${item.id.slice(-4)}` : item.id;

            return (
              <motion.div
                key={item.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05, duration: 0.3 }}
                className="relative pl-14"
              >
                {/* Timeline dot */}
                <div className="absolute left-[18px] top-5 w-3 h-3 rounded-full bg-white border-2 border-black/40 z-10" />

                {/* Card */}
                <div
                  className="glass-card p-4 cursor-pointer group"
                  onClick={() => toggle(item.id)}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <HashtagIcon className="w-3.5 h-3.5 text-gray-600" />
                      <span className="text-xs font-mono text-gray-500">{shortId}</span>
                    </div>
                    <button className="p-1 rounded hover:bg-black/5 transition-colors">
                      {isExpanded ? (
                        <ChevronUpIcon className="w-4 h-4 text-gray-500" />
                      ) : (
                        <ChevronDownIcon className="w-4 h-4 text-gray-500" />
                      )}
                    </button>
                  </div>

                  <p className={`text-sm text-gray-700 leading-relaxed ${isExpanded ? '' : 'line-clamp-2'}`}>
                    {item.text}
                  </p>

                  {isExpanded && item.metadata && Object.keys(item.metadata).length > 0 && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      className="mt-3 pt-3 border-t border-black/5"
                    >
                      <pre className="text-xs font-mono text-gray-400 whitespace-pre-wrap">
                        {JSON.stringify(item.metadata, null, 2)}
                      </pre>
                    </motion.div>
                  )}
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default TimelinePage;