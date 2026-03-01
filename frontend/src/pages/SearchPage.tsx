import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useApi } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useNavigate, useSearchParams } from 'react-router-dom';
import EmptyState from '../components/EmptyState';
import {
  MagnifyingGlassIcon,
  SparklesIcon,
  ArrowPathIcon,
  DocumentTextIcon,
} from '@heroicons/react/24/outline';

const SearchPage: React.FC = () => {
  const { token } = useAuth();
  const api = useApi();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [query, setQuery] = useState(searchParams.get('q') || '');
  const [results, setResults] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const runSearch = async (q?: string) => {
    const searchQuery = q || query;
    if (!token || !searchQuery.trim()) return;
    navigate(`/search?q=${encodeURIComponent(searchQuery)}`, { replace: true });
    setLoading(true);
    setError(null);
    try {
      const resp = await api.post(
        '/api/memory/recall',
        { query: searchQuery, max_tokens: 2000 },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setResults(resp.data.context);
      setSearched(true);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const q = searchParams.get('q');
    if (q && token) {
      setQuery(q);
      runSearch(q);
    }
  }, []);

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') runSearch();
  };

  if (!token) {
    return (
      <EmptyState
        icon={MagnifyingGlassIcon}
        title="Search Memories"
        description="Authenticate to search across your memory store."
        action={{ label: 'Go to Playground', onClick: () => navigate('/demo') }}
      />
    );
  }

  return (
    <div className="max-w-3xl mx-auto">
      {/* Search input */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-card p-1.5 flex items-center gap-2 mb-6"
      >
        <div className="pl-3">
          <MagnifyingGlassIcon className="w-5 h-5 text-gray-400" />
        </div>
        <input
          className="flex-1 bg-transparent text-gray-900 placeholder-gray-400 py-3 px-2 text-sm focus:outline-none"
          placeholder="Search your memories with natural language..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={onKeyDown}
          autoFocus
        />
        <button
          onClick={() => runSearch()}
          disabled={loading || !query.trim()}
          className="btn-glow flex items-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {loading ? (
            <ArrowPathIcon className="w-4 h-4 animate-spin" />
          ) : (
            <SparklesIcon className="w-4 h-4" />
          )}
          <span className="text-sm">Recall</span>
        </button>
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

      {/* Results */}
      <AnimatePresence>
        {results && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass-card p-6"
          >
            <div className="flex items-center gap-2 mb-4">
              <DocumentTextIcon className="w-5 h-5 text-cyan-400" />
              <h3 className="text-sm font-semibold text-gray-900">Recalled Context</h3>
            </div>
            <div className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap font-mono bg-black/[0.02] rounded-xl p-4 border border-black/10">
              {results}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Empty state */}
      {!searched && !loading && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-center py-16"
        >
          <MagnifyingGlassIcon className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <p className="text-sm text-gray-400">
            Type a query and press Enter or click Recall to search your memories.
          </p>
        </motion.div>
      )}
    </div>
  );
};

export default SearchPage;