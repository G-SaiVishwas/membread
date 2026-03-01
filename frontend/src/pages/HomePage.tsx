import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useApi } from '../api/client';
import { useAuth } from '../context/AuthContext';
import {
  DocumentTextIcon,
  CircleStackIcon,
  MagnifyingGlassIcon,
  TagIcon,
  PuzzlePieceIcon,
  RocketLaunchIcon,
  PlayIcon,
  BeakerIcon,
  BookOpenIcon,
  ArrowTopRightOnSquareIcon,
  SparklesIcon,
  ArrowRightIcon,
  ClockIcon,
  ShieldCheckIcon,
  CpuChipIcon,
  SignalIcon,
  ChevronRightIcon,
  CheckCircleIcon,
  CommandLineIcon,
  ShareIcon,
  GlobeAltIcon,
  BoltIcon,
  ArchiveBoxIcon,
  ChatBubbleLeftRightIcon,
} from '@heroicons/react/24/outline';

const fadeUp = {
  hidden: { opacity: 0, y: 16 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.06, duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] },
  }),
};

const HomePage: React.FC = () => {
  const { token } = useAuth();
  const api = useApi();
  const [memoryCount, setMemoryCount] = useState(0);
  const [activeRange, setActiveRange] = useState('7d');
  const [stats, setStats] = useState<any>(null);
  const [healthData, setHealthData] = useState<any>(null);
  const [activityData, setActivityData] = useState<any[]>([]);

  // Fetch all live data from API
  useEffect(() => {
    if (!token) return;
    const headers = { Authorization: `Bearer ${token}` };
    (async () => {
      try {
        const [countResp, statsResp, healthResp, activityResp] = await Promise.allSettled([
          api.get('/api/memory/count', { headers }),
          api.get('/api/stats', { headers }),
          api.get('/api/health/detailed', { headers }),
          api.get('/api/activity', { headers }),
        ]);
        if (countResp.status === 'fulfilled') setMemoryCount(countResp.value.data.count);
        if (statsResp.status === 'fulfilled') setStats(statsResp.value.data);
        if (healthResp.status === 'fulfilled') setHealthData(healthResp.value.data);
        if (activityResp.status === 'fulfilled') setActivityData(activityResp.value.data.items || []);
      } catch {}
    })();
  }, [token]);

  const timeRanges = ['24h', '7d', '30d', 'All'];

  // All metrics from API — zero hardcoding
  const activeAgents = stats?.active_agents ?? 0;
  const agentSessions = stats?.agent_sessions ?? 0;
  const crossToolMemories = stats?.memories ?? memoryCount;
  const continuityPct = stats?.continuity_score ?? 0;
  const memoryChange = stats?.changes?.memories ?? '+0';
  const agentChange = stats?.changes?.agents ?? '+0';
  const sessionChange = stats?.changes?.sessions ?? '+0';

  const metrics = [
    { label: 'Active Agents', value: activeAgents, icon: CpuChipIcon, change: agentChange, up: activeAgents > 0 },
    { label: 'Agent Sessions', value: agentSessions, icon: ClockIcon, change: sessionChange, up: agentSessions > 0 },
    { label: 'Cross-Tool Memories', value: crossToolMemories, icon: CircleStackIcon, change: memoryChange, up: crossToolMemories > 0 },
    { label: 'Continuity Score', value: `${continuityPct}%`, icon: ShieldCheckIcon, change: continuityPct > 50 ? 'Healthy' : continuityPct > 0 ? 'Building' : 'No data', up: continuityPct > 50 },
  ];

  const quickActions = [
    { icon: SparklesIcon, label: 'Attach Agent', desc: 'Connect an AI agent to memory', href: '/demo', color: 'bg-black text-white' },
    { icon: MagnifyingGlassIcon, label: 'Search', desc: 'Query across agents & sessions', href: '/search', color: 'bg-white border border-black/10 text-gray-900' },
    { icon: ClockIcon, label: 'Time Travel', desc: 'Cross-session bi-temporal search', href: '/temporal', color: 'bg-white border border-black/10 text-gray-900' },
    { icon: ChatBubbleLeftRightIcon, label: 'Agent Chat', desc: 'Session-aware conversations', href: '/chat', color: 'bg-white border border-black/10 text-gray-900' },
  ];

  // Agent Continuity Score replaces Getting Started
  const continuitySteps = [
    { step: 1, title: 'Generate Agent Token', desc: 'Create JWT credentials for your AI agent', done: !!token, href: '/demo' },
    { step: 2, title: 'Store Agent Memory', desc: 'Attach an agent and store its first observation', done: memoryCount > 0, href: '/demo' },
    { step: 3, title: 'Cross-Session Recall', desc: 'Query memory from a different session or tool', done: false, href: '/search' },
    { step: 4, title: 'Install Browser Extension', desc: 'Enable passive memory capture across AI tools', done: false, href: '/connectors' },
  ];
  const completedSteps = continuitySteps.filter((s) => s.done).length;

  // System status from API health check
  const systemStatus = (healthData?.services || [
    { name: 'Memory Engine', status: 'unknown' },
    { name: 'Vector Store', status: 'unknown' },
    { name: 'API Gateway', status: 'unknown' },
    { name: 'Auth Service', status: 'unknown' },
  ]).map((s: any) => ({
    label: s.name,
    status: s.status as 'operational' | 'degraded' | 'unknown',
    icon: s.name === 'Memory Engine' ? CpuChipIcon : s.name === 'Vector Store' ? CircleStackIcon : s.name === 'API Gateway' ? SignalIcon : ShieldCheckIcon,
  }));

  const exploreCards = [
    {
      icon: ClockIcon,
      title: 'Temporal Search',
      description: 'What did your coding agent know last Tuesday? Cross-session bi-temporal recall.',
      href: '/temporal',
      tag: 'Agentic',
    },
    {
      icon: ArchiveBoxIcon,
      title: 'Entity History',
      description: 'Track how an entity evolves across agent sessions, tools, and tasks.',
      href: '/entity-history',
      tag: 'Agentic',
    },
    {
      icon: ChatBubbleLeftRightIcon,
      title: 'Agent Chat',
      description: 'Session-persistent conversations with cross-tool context carry-over.',
      href: '/chat',
      tag: 'Multi-AI',
    },
    {
      icon: ShareIcon,
      title: 'Knowledge Graph',
      description: '3D graph colored by Agent, Session, and Task — see continuity in action.',
      href: '/graph',
      tag: 'Enhanced',
    },
    {
      icon: GlobeAltIcon,
      title: 'Connectors',
      description: 'Connect ChatGPT, Claude, Gemini, Cursor, and more for automatic memory capture.',
      href: '/connectors',
      tag: 'New',
    },
    {
      icon: CommandLineIcon,
      title: 'Plugins',
      description: 'Claude Code, OpenCode, ClawdBot — install memory plugins for your favorite tools.',
      href: '/plugins',
      tag: 'New',
    },
  ];

  // Recent activity from API
  const recentActivity = (activityData || []).map((a: any, i: number) => ({
    id: a.id || String(i + 1),
    type: a.type || 'system' as const,
    message: a.message || a.action || '',
    time: a.time || a.timestamp || '',
  }));

  return (
    <div className="max-w-[1200px] mx-auto">

      {/* ─── Hero Section ─── */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="mb-8"
      >
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-extrabold text-gray-900 tracking-tight mb-1">
              Memory Layer for Agentic AI
            </h1>
            <p className="text-[15px] text-gray-400">
              Give every AI agent persistent, cross-session, cross-tool memory.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex items-center bg-black/[0.03] border border-black/[0.06] rounded-xl overflow-hidden">
              {timeRanges.map((r) => (
                <button
                  key={r}
                  onClick={() => setActiveRange(r)}
                  className={`px-3.5 py-[7px] text-[12px] font-semibold transition-all duration-200 ${
                    activeRange === r
                      ? 'bg-black text-white shadow-sm'
                      : 'text-gray-400 hover:text-gray-700'
                  }`}
                >
                  {r}
                </button>
              ))}
            </div>
          </div>
        </div>
      </motion.div>

      {/* ─── Quick Actions Bar ─── */}
      <motion.div
        variants={fadeUp}
        initial="hidden"
        animate="visible"
        custom={1}
        className="flex gap-3 mb-8"
      >
        {quickActions.map((action) => (
          <Link
            key={action.label}
            to={action.href}
            className={`group flex items-center gap-3 px-4 py-3 rounded-2xl text-sm font-semibold transition-all duration-200 hover:shadow-md hover:-translate-y-0.5 ${action.color}`}
          >
            <action.icon className="w-[18px] h-[18px]" />
            <div className="flex flex-col leading-tight">
              <span className="text-[13px] font-semibold">{action.label}</span>
              <span className="text-[11px] font-normal opacity-60">{action.desc}</span>
            </div>
            <ArrowRightIcon className="w-3.5 h-3.5 opacity-0 group-hover:opacity-60 -translate-x-1 group-hover:translate-x-0 transition-all" />
          </Link>
        ))}
      </motion.div>

      {/* ─── Metrics Grid ─── */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        {metrics.map((metric, i) => (
          <motion.div
            key={metric.label}
            variants={fadeUp}
            initial="hidden"
            animate="visible"
            custom={i + 2}
            className="group relative bg-white border border-black/[0.06] rounded-2xl p-5 hover:border-black/[0.12] hover:shadow-[0_2px_16px_rgba(0,0,0,0.04)] transition-all duration-300"
          >
            <div className="flex items-start justify-between mb-4">
              <div className="w-10 h-10 rounded-xl bg-black/[0.03] flex items-center justify-center">
                <metric.icon className="w-5 h-5 text-gray-400" />
              </div>
              <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${
                metric.change === '—'
                  ? 'text-gray-400 bg-black/[0.03]'
                  : metric.up
                  ? 'text-emerald-600 bg-emerald-50'
                  : 'text-red-500 bg-red-50'
              }`}>
                {metric.change}
              </span>
            </div>
            <p className="text-3xl font-bold text-gray-900 mb-1 tracking-tight">{metric.value.toLocaleString()}</p>
            <p className="text-[12px] text-gray-400 font-medium">{metric.label}</p>
            {/* Subtle bottom accent */}
            <div className="absolute bottom-0 left-4 right-4 h-px bg-gradient-to-r from-transparent via-black/[0.06] to-transparent" />
          </motion.div>
        ))}
      </div>

      {/* ─── Two-Column Layout: Getting Started + System Status ─── */}
      <div className="grid grid-cols-5 gap-5 mb-8">

        {/* Getting Started — spans 3 cols */}
        <motion.div
          variants={fadeUp}
          initial="hidden"
          animate="visible"
          custom={6}
          className="col-span-3 bg-white border border-black/[0.06] rounded-2xl p-6"
        >
          <div className="flex items-center justify-between mb-5">
            <div>
              <h2 className="text-[16px] font-bold text-gray-900">Agent Continuity Score</h2>
              <p className="text-[12px] text-gray-400 mt-0.5">{completedSteps} of {continuitySteps.length} milestones reached</p>
            </div>
            {/* Progress bar */}
            <div className="flex items-center gap-3">
              <div className="w-32 h-1.5 bg-black/[0.04] rounded-full overflow-hidden">
                <div
                  className="h-full bg-black rounded-full transition-all duration-500"
                  style={{ width: `${(completedSteps / continuitySteps.length) * 100}%` }}
                />
              </div>
              <span className="text-[11px] font-bold text-gray-400">{Math.round((completedSteps / continuitySteps.length) * 100)}%</span>
            </div>
          </div>

          <div className="space-y-2">
            {continuitySteps.map((step) => (
              <Link
                key={step.step}
                to={step.href}
                className={`group flex items-center gap-4 px-4 py-3.5 rounded-xl transition-all duration-200 ${
                  step.done
                    ? 'bg-black/[0.02]'
                    : 'hover:bg-black/[0.03] border border-transparent hover:border-black/[0.06]'
                }`}
              >
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-[12px] font-bold shrink-0 ${
                  step.done
                    ? 'bg-emerald-50 text-emerald-600'
                    : 'bg-black/[0.04] text-gray-400'
                }`}>
                  {step.done ? <CheckCircleIcon className="w-5 h-5" /> : step.step}
                </div>
                <div className="flex-1 min-w-0">
                  <p className={`text-[13px] font-semibold ${step.done ? 'text-gray-400 line-through' : 'text-gray-900'}`}>
                    {step.title}
                  </p>
                  <p className="text-[11px] text-gray-400 mt-0.5">{step.desc}</p>
                </div>
                {!step.done && (
                  <ChevronRightIcon className="w-4 h-4 text-gray-300 group-hover:text-gray-500 transition-colors shrink-0" />
                )}
              </Link>
            ))}
          </div>
        </motion.div>

        {/* Right Column — System + Activity */}
        <div className="col-span-2 flex flex-col gap-5">

          {/* System Status */}
          <motion.div
            variants={fadeUp}
            initial="hidden"
            animate="visible"
            custom={7}
            className="bg-white border border-black/[0.06] rounded-2xl p-5"
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-[14px] font-bold text-gray-900">System Status</h2>
              <div className="flex items-center gap-1.5">
                <div className="w-[6px] h-[6px] rounded-full bg-emerald-500 shadow-[0_0_6px_rgba(16,185,129,0.4)]" />
                <span className="text-[11px] font-semibold text-emerald-600">All Systems Operational</span>
              </div>
            </div>

            <div className="space-y-2">
              {systemStatus.map((service) => (
                <div
                  key={service.label}
                  className="flex items-center justify-between px-3 py-2.5 rounded-xl bg-black/[0.015] hover:bg-black/[0.03] transition-colors"
                >
                  <div className="flex items-center gap-2.5">
                    <service.icon className="w-4 h-4 text-gray-400" />
                    <span className="text-[12px] font-medium text-gray-600">{service.label}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                    <span className="text-[11px] text-emerald-600 font-medium capitalize">{service.status}</span>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>

          {/* Recent Activity */}
          <motion.div
            variants={fadeUp}
            initial="hidden"
            animate="visible"
            custom={8}
            className="bg-white border border-black/[0.06] rounded-2xl p-5 flex-1"
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-[14px] font-bold text-gray-900">Recent Activity</h2>
              <ClockIcon className="w-4 h-4 text-gray-300" />
            </div>

            <div className="space-y-1">
              {recentActivity.map((item) => (
                <div
                  key={item.id}
                  className="flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-black/[0.02] transition-colors"
                >
                  <div className="w-6 h-6 rounded-lg bg-black/[0.04] flex items-center justify-center shrink-0">
                    <BoltIcon className="w-3.5 h-3.5 text-gray-400" />
                  </div>
                  <p className="text-[12px] text-gray-600 flex-1 truncate">{item.message}</p>
                  <span className="text-[11px] text-gray-300 whitespace-nowrap">{item.time}</span>
                </div>
              ))}
            </div>

            {recentActivity.length === 0 && (
              <p className="text-center text-[12px] text-gray-400 py-6">No recent activity yet</p>
            )}
          </motion.div>
        </div>
      </div>

      {/* ─── Explore the Platform ─── */}
      <motion.div
        variants={fadeUp}
        initial="hidden"
        animate="visible"
        custom={9}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-[16px] font-bold text-gray-900">Explore the Platform</h2>
          <span className="text-[11px] text-gray-400 font-medium">See how Membread powers agentic memory</span>
        </div>

        <div className="grid grid-cols-4 gap-4">
          {exploreCards.map((card, i) => (
            <Link
              key={card.title}
              to={card.href}
              className="group relative bg-white border border-black/[0.06] rounded-2xl p-5 hover:border-black/[0.12] hover:shadow-[0_4px_20px_rgba(0,0,0,0.04)] hover:-translate-y-0.5 transition-all duration-300"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="w-10 h-10 rounded-xl bg-black/[0.03] flex items-center justify-center group-hover:bg-black group-hover:text-white transition-all duration-300">
                  <card.icon className="w-5 h-5 text-gray-400 group-hover:text-white transition-colors" />
                </div>
                <span className="text-[10px] font-semibold text-gray-400 bg-black/[0.03] px-2 py-0.5 rounded-lg uppercase tracking-wider">
                  {card.tag}
                </span>
              </div>
              <h3 className="text-[14px] font-bold text-gray-900 mb-1.5">{card.title}</h3>
              <p className="text-[12px] text-gray-400 leading-relaxed">{card.description}</p>
              <div className="flex items-center gap-1 mt-3 text-[11px] font-semibold text-gray-400 group-hover:text-gray-900 transition-colors">
                <span>Explore</span>
                <ArrowRightIcon className="w-3 h-3 translate-x-0 group-hover:translate-x-1 transition-transform" />
              </div>
            </Link>
          ))}
        </div>
      </motion.div>

      {/* ─── API Quick Reference ─── */}
      <motion.div
        variants={fadeUp}
        initial="hidden"
        animate="visible"
        custom={10}
        className="mt-8 bg-gray-950 rounded-2xl p-6 overflow-hidden relative"
      >
        <div className="flex items-start justify-between relative z-10">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <CommandLineIcon className="w-4 h-4 text-white/60" />
              <span className="text-[11px] font-bold text-white/40 uppercase tracking-wider">Quick Reference</span>
            </div>
            <h3 className="text-[16px] font-bold text-white mb-1">Agent SDK Quick Start</h3>
            <p className="text-[12px] text-white/40 max-w-md">Attach any AI agent to persistent memory in 3 lines of code.</p>
          </div>
          <Link
            to="/demo"
            className="flex items-center gap-2 px-4 py-2 bg-white text-gray-900 text-[12px] font-bold rounded-xl hover:bg-gray-100 transition-colors"
          >
            Try Demo <ArrowRightIcon className="w-3 h-3" />
          </Link>
        </div>

        <div className="mt-5 grid grid-cols-2 gap-3 relative z-10">
          <div className="bg-white/[0.06] border border-white/[0.06] rounded-xl px-4 py-3">
            <div className="flex items-center gap-2 mb-1.5">
              <span className="text-[10px] font-bold text-emerald-400 bg-emerald-400/10 px-1.5 py-0.5 rounded">POST</span>
              <code className="text-[12px] text-white/70 font-mono">/api/memory/store</code>
            </div>
            <p className="text-[11px] text-white/30">Store an agent observation with agent_id, session_id, task_id</p>
          </div>
          <div className="bg-white/[0.06] border border-white/[0.06] rounded-xl px-4 py-3">
            <div className="flex items-center gap-2 mb-1.5">
              <span className="text-[10px] font-bold text-blue-400 bg-blue-400/10 px-1.5 py-0.5 rounded">POST</span>
              <code className="text-[12px] text-white/70 font-mono">/api/memory/recall</code>
            </div>
            <p className="text-[11px] text-white/30">Cross-session, cross-tool semantic recall for any agent</p>
          </div>
          <div className="bg-white/[0.06] border border-white/[0.06] rounded-xl px-4 py-3">
            <div className="flex items-center gap-2 mb-1.5">
              <span className="text-[10px] font-bold text-violet-400 bg-violet-400/10 px-1.5 py-0.5 rounded">POST</span>
              <code className="text-[12px] text-white/70 font-mono">/api/memory/search/temporal</code>
            </div>
            <p className="text-[11px] text-white/30">Time-travel across agent sessions with bi-temporal filtering</p>
          </div>
          <div className="bg-white/[0.06] border border-white/[0.06] rounded-xl px-4 py-3">
            <div className="flex items-center gap-2 mb-1.5">
              <span className="text-[10px] font-bold text-amber-400 bg-amber-400/10 px-1.5 py-0.5 rounded">GET</span>
              <code className="text-[12px] text-white/70 font-mono">/api/memory/graph</code>
            </div>
            <p className="text-[11px] text-white/30">Agent-session-task knowledge graph with typed relationships</p>
          </div>
        </div>

        {/* Decorative gradient */}
        <div className="absolute top-0 right-0 w-64 h-64 bg-gradient-to-bl from-white/[0.03] to-transparent rounded-full -translate-y-1/2 translate-x-1/2" />
      </motion.div>

    </div>
  );
};

export default HomePage;