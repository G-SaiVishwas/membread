import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useApi } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import EmptyState from '../components/EmptyState';
import {
  ArchiveBoxIcon,
  MagnifyingGlassIcon,
  ArrowPathIcon,
  CalendarDaysIcon,
  ChevronRightIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  UserIcon,
  CubeIcon,
} from '@heroicons/react/24/outline';

interface EntityVersion {
  entity_id: string;
  name: string;
  properties: Record<string, any>;
  valid_from: string | null;
  valid_until: string | null;
}

interface HistoryResult {
  entity_name: string;
  versions: EntityVersion[];
}

const SUGGESTED_ENTITIES = [
  { name: 'coding-agent-1', icon: CubeIcon, color: 'bg-violet-50 text-violet-600 border-violet-200' },
  { name: 'research-session', icon: CubeIcon, color: 'bg-orange-50 text-orange-600 border-orange-200' },
  { name: 'Project Phoenix', icon: CubeIcon, color: 'bg-amber-50 text-amber-600 border-amber-200' },
  { name: 'deployment-task', icon: CubeIcon, color: 'bg-emerald-50 text-emerald-600 border-emerald-200' },
];

const EntityHistoryPage: React.FC = () => {
  const { token } = useAuth();
  const api = useApi();
  const navigate = useNavigate();
  const [entityName, setEntityName] = useState('');
  const [result, setResult] = useState<HistoryResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  const fetchHistory = async (name?: string) => {
    const target = name || entityName.trim();
    if (!token || !target) return;
    if (name) setEntityName(name);
    setLoading(true);
    setError(null);
    try {
      const resp = await api.post(
        '/api/memory/entity/history',
        { entity_name: target },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setResult(resp.data);
      setSearched(true);
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message);
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') fetchHistory();
  };

  if (!token) {
    return (
      <EmptyState
        icon={ArchiveBoxIcon}
        title="Agent Entity History"
        description="Authenticate to explore how entities evolve across agent sessions."
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
          <ArchiveBoxIcon className="w-6 h-6 text-gray-900" />
          <h1 className="text-2xl font-extrabold text-gray-900 tracking-tight">
            Agent Entity History
          </h1>
        </div>
        <p className="text-sm text-gray-400 ml-9">
          Track how an entity <strong className="text-gray-600">evolves across agent sessions and tools</strong>.
          View every version with{' '}
          <code className="text-xs bg-black/5 px-1.5 py-0.5 rounded">valid_from</code> /{' '}
          <code className="text-xs bg-black/5 px-1.5 py-0.5 rounded">valid_until</code> windows.
        </p>
      </motion.div>

      {/* Search */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.05 }}
        className="glass-card p-5 mb-6"
      >
        <label className="block text-xs font-medium text-gray-500 mb-1.5">Entity Name</label>
        <div className="flex gap-3">
          <div className="relative flex-1">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              className="input-dark pl-10"
              placeholder="e.g. coding-agent-1, research-session, deployment-task..."
              value={entityName}
              onChange={(e) => setEntityName(e.target.value)}
              onKeyDown={onKeyDown}
            />
          </div>
          <button
            onClick={() => fetchHistory()}
            disabled={loading || !entityName.trim()}
            className="btn-glow flex items-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {loading ? (
              <ArrowPathIcon className="w-4 h-4 animate-spin" />
            ) : (
              <ArchiveBoxIcon className="w-4 h-4" />
            )}
            <span className="text-sm">Lookup</span>
          </button>
        </div>

        {/* Suggested entities */}
        <div className="mt-3 flex items-center gap-2">
          <span className="text-[11px] text-gray-400 font-medium">Try:</span>
          {SUGGESTED_ENTITIES.map((ent) => (
            <button
              key={ent.name}
              onClick={() => fetchHistory(ent.name)}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-[11px] font-medium transition-colors hover:shadow-sm ${ent.color}`}
            >
              <ent.icon className="w-3 h-3" />
              {ent.name}
            </button>
          ))}
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

      {/* Results */}
      <AnimatePresence>
        {result && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            {/* Entity header */}
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <span className="text-sm font-bold text-gray-900">{result.entity_name}</span>
                <span className="text-[11px] font-semibold text-gray-400 bg-black/[0.04] px-2 py-0.5 rounded-lg">
                  {result.versions.length} version{result.versions.length !== 1 ? 's' : ''}
                </span>
              </div>
            </div>

            {result.versions.length === 0 ? (
              <div className="glass-card p-8 text-center">
                <ArchiveBoxIcon className="w-10 h-10 text-gray-300 mx-auto mb-3" />
                <p className="text-sm text-gray-400">No version history found for this entity.</p>
              </div>
            ) : (
              <div className="relative">
                {/* Timeline line */}
                <div className="absolute left-6 top-0 bottom-0 w-px bg-black/[0.08]" />

                <div className="space-y-4">
                  {result.versions.map((ver, i) => {
                    const isCurrent = !ver.valid_until;
                    return (
                      <motion.div
                        key={ver.entity_id || i}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: i * 0.06, duration: 0.3 }}
                        className="relative pl-14"
                      >
                        {/* Timeline dot */}
                        <div
                          className={`absolute left-[18px] top-5 w-3 h-3 rounded-full border-2 z-10 ${
                            isCurrent
                              ? 'bg-emerald-500 border-emerald-200 shadow-[0_0_8px_rgba(16,185,129,0.4)]'
                              : 'bg-white border-gray-300'
                          }`}
                        />

                        <div
                          className={`glass-card p-4 ${
                            isCurrent ? 'ring-1 ring-emerald-200' : ''
                          }`}
                        >
                          {/* Version header */}
                          <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center gap-2">
                              {isCurrent ? (
                                <span className="flex items-center gap-1 text-[11px] font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-lg">
                                  <CheckCircleIcon className="w-3 h-3" />
                                  Current
                                </span>
                              ) : (
                                <span className="flex items-center gap-1 text-[11px] font-bold text-gray-400 bg-gray-50 px-2 py-0.5 rounded-lg">
                                  <XCircleIcon className="w-3 h-3" />
                                  Superseded
                                </span>
                              )}
                              <span className="text-[11px] font-semibold text-gray-500">
                                v{result.versions.length - i}
                              </span>
                            </div>
                            {ver.entity_id && (
                              <span className="text-[10px] font-mono text-gray-300 truncate max-w-[120px]">
                                {ver.entity_id}
                              </span>
                            )}
                          </div>

                          {/* Name */}
                          <p className="text-sm font-semibold text-gray-900 mb-2">{ver.name}</p>

                          {/* Validity window */}
                          <div className="flex items-center gap-3 mb-3 text-[11px] text-gray-400">
                            <span className="flex items-center gap-1">
                              <CalendarDaysIcon className="w-3 h-3" />
                              From:{' '}
                              {ver.valid_from
                                ? new Date(ver.valid_from).toLocaleString()
                                : '—'}
                            </span>
                            <ChevronRightIcon className="w-3 h-3" />
                            <span className="flex items-center gap-1">
                              <ClockIcon className="w-3 h-3" />
                              Until:{' '}
                              {ver.valid_until
                                ? new Date(ver.valid_until).toLocaleString()
                                : 'present'}
                            </span>
                          </div>

                          {/* Properties */}
                          {ver.properties && Object.keys(ver.properties).length > 0 && (
                            <div className="bg-black/[0.02] rounded-xl p-3">
                              <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2">
                                Properties
                              </p>
                              <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
                                {Object.entries(ver.properties).map(([key, val]) => (
                                  <div key={key} className="flex items-baseline gap-1.5">
                                    <span className="text-[11px] font-medium text-gray-500">
                                      {key}:
                                    </span>
                                    <span className="text-[11px] text-gray-700 font-mono truncate">
                                      {typeof val === 'object'
                                        ? JSON.stringify(val)
                                        : String(val)}
                                    </span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      </motion.div>
                    );
                  })}
                </div>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Initial state */}
      {!searched && !result && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.15 }}
          className="glass-card p-12 text-center"
        >
          <ArchiveBoxIcon className="w-12 h-12 text-gray-200 mx-auto mb-4" />
          <h3 className="text-sm font-bold text-gray-900 mb-1">
            Look up an agent entity
          </h3>
          <p className="text-xs text-gray-400 max-w-sm mx-auto">
            Enter a name above to see its full version history — every change tracked
            across agent sessions with bi-temporal validity windows.
          </p>
        </motion.div>
      )}
    </div>
  );
};

export default EntityHistoryPage;
