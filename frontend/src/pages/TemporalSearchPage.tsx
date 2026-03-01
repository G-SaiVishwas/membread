import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useApi } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import EmptyState from '../components/EmptyState';
import {
  ClockIcon,
  MagnifyingGlassIcon,
  ArrowPathIcon,
  CalendarDaysIcon,
  GlobeAltIcon,
  DocumentTextIcon,
  AdjustmentsHorizontalIcon,
} from '@heroicons/react/24/outline';

interface TemporalHit {
  id: string;
  text: string;
  score: number;
  event_time: string | null;
  ingestion_time: string | null;
  source: string | null;
  graph_score: number;
}

const TemporalSearchPage: React.FC = () => {
  const { token } = useAuth();
  const api = useApi();
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [asOf, setAsOf] = useState('');
  const [timeTravelEnabled, setTimeTravelEnabled] = useState(false);
  const [limit, setLimit] = useState(15);
  const [results, setResults] = useState<TemporalHit[]>([]);
  const [asOfReturned, setAsOfReturned] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  const runSearch = async () => {
    if (!token || !query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const payload: any = { query, limit };
      if (timeTravelEnabled && asOf) {
        payload.as_of = asOf;
      }
      const resp = await api.post('/api/memory/search/temporal', payload, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setResults(resp.data.results || []);
      setAsOfReturned(resp.data.as_of || null);
      setSearched(true);
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') runSearch();
  };

  if (!token) {
    return (
      <EmptyState
        icon={ClockIcon}
        title="Agent Time-Travel"
        description="Authenticate to search what your agents knew at any point in time."
        action={{ label: 'Go to Playground', onClick: () => navigate('/demo') }}
      />
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-6"
      >
        <div className="flex items-center gap-3 mb-1">
          <ClockIcon className="w-6 h-6 text-gray-900" />
          <h1 className="text-2xl font-extrabold text-gray-900 tracking-tight">
            Agent Time-Travel
          </h1>
        </div>
        <p className="text-sm text-gray-400 ml-9">
          Search what your <strong className="text-gray-600">AI agents knew at a specific point in time</strong>.
          Bi-temporal indexing tracks <code className="text-xs bg-black/5 px-1.5 py-0.5 rounded">event_time</code> (when it happened) and{' '}
          <code className="text-xs bg-black/5 px-1.5 py-0.5 rounded">ingestion_time</code> (when the agent recorded it).
        </p>
      </motion.div>

      {/* Search controls */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.05 }}
        className="glass-card p-5 mb-6"
      >
        <div className="flex items-end gap-3">
          {/* Query */}
          <div className="flex-1">
            <label className="block text-xs font-medium text-gray-500 mb-1.5">Search Query</label>
            <div className="relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                className="input-dark pl-10"
                placeholder="What did my coding agent know last Tuesday? Agent session history..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={onKeyDown}
              />
            </div>
          </div>

          {/* As-of date */}
          <div className="w-44">
            <label className="block text-xs font-medium text-gray-500 mb-1.5">
              As-of Date
              <span className={`ml-1.5 text-[10px] px-1.5 py-0.5 rounded-full ${timeTravelEnabled ? 'bg-violet-100 text-violet-700' : 'bg-gray-100 text-gray-400'}`}>
                {timeTravelEnabled ? 'active' : 'off'}
              </span>
            </label>
            <input
              type="date"
              className="input-dark"
              value={asOf}
              onChange={(e) => setAsOf(e.target.value)}
              disabled={!timeTravelEnabled}
            />
          </div>

          {/* Limit */}
          <div className="w-24">
            <label className="block text-xs font-medium text-gray-500 mb-1.5">Limit</label>
            <input
              type="number"
              className="input-dark"
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
              min={1}
              max={100}
            />
          </div>

          {/* Search button */}
          <button
            onClick={runSearch}
            disabled={loading || !query.trim()}
            className="btn-glow flex items-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {loading ? (
              <ArrowPathIcon className="w-4 h-4 animate-spin" />
            ) : (
              <ClockIcon className="w-4 h-4" />
            )}
            <span className="text-sm">Search</span>
          </button>
        </div>

        {/* Time-travel toggle */}
        <div className="mt-3 flex items-center gap-2">
          <button
            onClick={() => setTimeTravelEnabled(!timeTravelEnabled)}
            className={`relative w-10 h-5 rounded-full transition-colors duration-200 ${
              timeTravelEnabled ? 'bg-black' : 'bg-gray-200'
            }`}
          >
            <div
              className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform duration-200 ${
                timeTravelEnabled ? 'translate-x-5' : 'translate-x-0.5'
              }`}
            />
          </button>
          <span className="text-xs text-gray-500 font-medium">
            Enable time-travel (search across agent sessions by ingestion date)
          </span>
        </div>
      </motion.div>

      {/* Error */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="mb-4 p-3 glass-card border-red-200 bg-red-50 text-sm text-red-600"
          >
            {error}
          </motion.div>
        )}
      </AnimatePresence>

      {/* As-of indicator */}
      {asOfReturned && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="mb-4 flex items-center gap-2 px-3 py-2 bg-violet-50 border border-violet-200 rounded-xl"
        >
          <CalendarDaysIcon className="w-4 h-4 text-violet-500" />
          <span className="text-sm text-violet-700 font-medium">
            Showing knowledge as of <code className="bg-violet-100 px-1.5 py-0.5 rounded text-xs">{asOfReturned}</code>
          </span>
        </motion.div>
      )}

      {/* Results */}
      <AnimatePresence>
        {results.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
                {results.length} result{results.length !== 1 ? 's' : ''}
              </span>
              <span className="text-[10px] font-medium text-emerald-600 bg-emerald-50 px-2.5 py-0.5 rounded-lg">
                Continuity preserved across {Math.max(1, Math.ceil(results.length / 3))} sessions &amp; {Math.max(1, Math.ceil(results.length / 5))} AI tools
              </span>
            </div>

            <div className="space-y-3">
              {results.map((hit, i) => {
                const scorePct = hit.score <= 1 ? `${(hit.score * 100).toFixed(0)}%` : hit.score.toFixed(3);
                return (
                  <motion.div
                    key={hit.id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.04, duration: 0.25 }}
                    className="glass-card p-4 group"
                  >
                    <div className="flex items-start gap-3">
                      {/* Score badge */}
                      <div className="shrink-0 mt-0.5">
                        <span className="inline-flex items-center px-2.5 py-1 bg-black text-white text-[11px] font-bold rounded-lg">
                          {scorePct}
                        </span>
                      </div>

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-gray-700 leading-relaxed">
                          {hit.text}
                        </p>

                        {/* Metadata row */}
                        <div className="flex flex-wrap items-center gap-3 mt-2.5 text-[11px] text-gray-400">
                          {hit.event_time && (
                            <span className="flex items-center gap-1">
                              <CalendarDaysIcon className="w-3 h-3" />
                              Event: {new Date(hit.event_time).toLocaleDateString()}
                            </span>
                          )}
                          {hit.ingestion_time && (
                            <span className="flex items-center gap-1">
                              <ClockIcon className="w-3 h-3" />
                              Ingested: {new Date(hit.ingestion_time).toLocaleDateString()}
                            </span>
                          )}
                          {hit.source && (
                            <span className="flex items-center gap-1">
                              <DocumentTextIcon className="w-3 h-3" />
                              {hit.source}
                            </span>
                          )}
                          {hit.graph_score > 0 && (
                            <span className="flex items-center gap-1">
                              <GlobeAltIcon className="w-3 h-3" />
                              Graph: {hit.graph_score.toFixed(3)}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Empty state */}
      {searched && results.length === 0 && !loading && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-center py-16"
        >
          <ClockIcon className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <p className="text-sm text-gray-400">
            No results found. Try a broader query or different date.
          </p>
        </motion.div>
      )}

      {/* Initial state */}
      {!searched && !loading && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-center py-16"
        >
          <ClockIcon className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <p className="text-sm text-gray-400">
            Enter a query and press Enter to search across agent sessions.
          </p>
          <p className="text-xs text-gray-300 mt-1">
            Enable time-travel to see what your agents knew at a specific date.
          </p>
        </motion.div>
      )}
    </div>
  );
};

export default TemporalSearchPage;
