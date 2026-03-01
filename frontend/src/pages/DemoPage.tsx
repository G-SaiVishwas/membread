import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useApi } from '../api/client';
import { useAuth } from '../context/AuthContext';
import {
  KeyIcon,
  CircleStackIcon,
  MagnifyingGlassCircleIcon,
  UserCircleIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  ClipboardDocumentIcon,
  ArrowPathIcon,
  CodeBracketIcon,
} from '@heroicons/react/24/outline';

const steps = [
  { id: 'auth', label: 'Authenticate', icon: KeyIcon },
  { id: 'store', label: 'Store', icon: CircleStackIcon },
  { id: 'recall', label: 'Recall', icon: MagnifyingGlassCircleIcon },
  { id: 'profile', label: 'Profile', icon: UserCircleIcon },
  { id: 'sdk', label: 'Agent SDK', icon: CodeBracketIcon },
];

const AGENT_PRESETS = [
  { id: 'custom', label: 'Custom Agent' },
  { id: 'langgraph', label: 'LangGraph Agent' },
  { id: 'crewai', label: 'CrewAI Team' },
  { id: 'autogen', label: 'AutoGen Agent' },
  { id: 'cursor', label: 'Cursor / Copilot' },
];

const SDK_EXAMPLES: Record<string, { label: string; code: string }> = {
  python: {
    label: 'Python',
    code: `from membread import Membread

tg = Membread(api_key="YOUR_KEY")

# Attach agent and store memory
tg.store(
    observation="User prefers dark mode in VS Code",
    agent_id="coding-agent-1",
    session_id="session-abc",
    task_id="setup-preferences"
)

# Cross-session recall
ctx = tg.recall(
    query="What are the user's editor preferences?",
    agent_id="coding-agent-1",
    cross_session=True   # searches ALL sessions
)
print(ctx.context)`,
  },
  langgraph: {
    label: 'LangGraph',
    code: `from membread.integrations import MembreadMemory
from langgraph.prebuilt import create_react_agent

memory = MembreadMemory(
    api_key="YOUR_KEY",
    agent_id="langgraph-research",
    persist_sessions=True
)

agent = create_react_agent(
    model, tools,
    checkpointer=memory  # every step auto-persisted
)

# Memory carries across sessions automatically
result = agent.invoke(
    {"messages": [("user", "Continue yesterday's research")]},
    config={"configurable": {"thread_id": "research-alpha"}}
)`,
  },
  crewai: {
    label: 'CrewAI',
    code: `from membread.integrations import MembreadCrewMemory
from crewai import Agent, Crew

memory = MembreadCrewMemory(
    api_key="YOUR_KEY",
    team_id="product-crew"
)

researcher = Agent(
    role="Researcher",
    memory=memory.for_agent("researcher"),
)

writer = Agent(
    role="Writer",
    memory=memory.for_agent("writer"),
    # Writer sees Researcher's memories too!
)

crew = Crew(agents=[researcher, writer])`,
  },
  autogen: {
    label: 'AutoGen',
    code: `from membread.integrations import MembreadAutoGen
import autogen

memory = MembreadAutoGen(
    api_key="YOUR_KEY",
    agent_id="autogen-assistant"
)

assistant = autogen.AssistantAgent(
    "assistant",
    llm_config=llm_config,
    memory=memory  # persistent across conversations
)

# Memory from previous chats is automatically loaded
user_proxy.initiate_chat(
    assistant,
    message="Pick up where we left off on the API design"
)`,
  },
};

const DemoPage: React.FC = () => {
  const [tenantId, setTenantId] = useState('demo-tenant');
  const [userId, setUserId] = useState('demo-user');
  const { token, setToken } = useAuth();
  const [observation, setObservation] = useState('');
  const [query, setQuery] = useState('');
  const [maxTokens, setMaxTokens] = useState(2000);
  const [result, setResult] = useState<null | { text: string; error?: boolean }>(null);
  const [loading, setLoading] = useState(false);
  const [activeStep, setActiveStep] = useState('auth');
  const [copied, setCopied] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState('custom');
  const [sessionId, setSessionId] = useState('session-001');
  const [crossSession, setCrossSession] = useState(false);
  const [sdkTab, setSdkTab] = useState('python');
  const [sdkCopied, setSdkCopied] = useState(false);

  const api = useApi();

  const run = async (fn: () => Promise<void>) => {
    setLoading(true);
    setResult(null);
    try {
      await fn();
    } catch (err: any) {
      setResult({ text: err.message, error: true });
    } finally {
      setLoading(false);
    }
  };

  const generateToken = () =>
    run(async () => {
      const resp = await api.post('/api/auth/token', { tenant_id: tenantId, user_id: userId });
      setToken(resp.data.token);
      setResult({ text: `Token generated. Expires in ${resp.data.expires_in_hours}h.` });
    });

  const storeObservation = () =>
    run(async () => {
      const resp = await api.post('/api/memory/store', { observation, metadata: {} }, { headers: { Authorization: `Bearer ${token}` } });
      setResult({ text: JSON.stringify(resp.data, null, 2) });
      setObservation('');
    });

  const recallContext = () =>
    run(async () => {
      const resp = await api.post('/api/memory/recall', { query, max_tokens: maxTokens }, { headers: { Authorization: `Bearer ${token}` } });
      setResult({ text: resp.data.context });
    });

  const getProfile = () =>
    run(async () => {
      const resp = await api.get('/api/memory/profile', { headers: { Authorization: `Bearer ${token}` } });
      setResult({ text: JSON.stringify(resp.data, null, 2) });
    });

  const copyToken = () => {
    navigator.clipboard.writeText(token);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="max-w-4xl mx-auto">
      {/* Step indicators */}
      <div className="flex items-center justify-center gap-2 mb-8">
        {steps.map((step, i) => (
          <React.Fragment key={step.id}>
            <button
              onClick={() => setActiveStep(step.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200
                ${activeStep === step.id
                  ? 'bg-black text-white'
                  : 'text-gray-400 hover:text-gray-900 hover:bg-black/[0.03]'}`}
            >
              <step.icon className="w-4 h-4" />
              <span className="hidden sm:inline">{step.label}</span>
            </button>
            {i < steps.length - 1 && <div className="w-8 h-px bg-black/10" />}
          </React.Fragment>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: input panel */}
        <motion.div key={activeStep} initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.25 }} className="glass-card p-6">
          {activeStep === 'auth' && (
            <div className="space-y-4">
              <h3 className="section-title"><KeyIcon className="w-5 h-5 text-gray-900" />Generate Agent Token</h3>
              <p className="text-sm text-gray-500">Create an auth token for your AI agent to access the memory layer.</p>
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1.5">Tenant ID</label>
                <input className="input-dark" value={tenantId} onChange={(e) => setTenantId(e.target.value)} />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1.5">User ID</label>
                <input className="input-dark" value={userId} onChange={(e) => setUserId(e.target.value)} />
              </div>
              <button onClick={generateToken} disabled={loading} className="btn-glow w-full flex items-center justify-center gap-2">
                {loading ? <ArrowPathIcon className="w-4 h-4 animate-spin" /> : <KeyIcon className="w-4 h-4" />}
                Generate Token
              </button>
              {token && (
                <div className="mt-3 p-3 bg-black/[0.02] rounded-xl border border-black/10">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs text-gray-500 font-medium">Current Token</span>
                    <button onClick={copyToken} className="flex items-center gap-1 text-xs text-gray-900 hover:text-gray-600">
                      <ClipboardDocumentIcon className="w-3.5 h-3.5" />{copied ? 'Copied!' : 'Copy'}
                    </button>
                  </div>
                  <p className="text-xs font-mono text-gray-400 break-all line-clamp-3">{token}</p>
                </div>
              )}
            </div>
          )}
          {activeStep === 'store' && (
            <div className="space-y-4">
              <h3 className="section-title"><CircleStackIcon className="w-5 h-5 text-gray-900" />Store Agent Observation</h3>
              <p className="text-sm text-gray-500">Attach an AI agent and store its observation in the temporal graph.</p>
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1.5">Attach to Agent</label>
                <select className="input-dark" value={selectedAgent} onChange={(e) => setSelectedAgent(e.target.value)}>
                  {AGENT_PRESETS.map((a) => <option key={a.id} value={a.id}>{a.label}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1.5">Session ID</label>
                <input className="input-dark" placeholder="session-001" value={sessionId} onChange={(e) => setSessionId(e.target.value)} />
              </div>
              <textarea className="input-dark h-24 resize-none" placeholder="Enter an agent observation..." value={observation} onChange={(e) => setObservation(e.target.value)} />
              <button onClick={storeObservation} disabled={loading || !token || !observation.trim()} className="btn-glow w-full flex items-center justify-center gap-2 disabled:opacity-40">
                {loading ? <ArrowPathIcon className="w-4 h-4 animate-spin" /> : <CircleStackIcon className="w-4 h-4" />}Store Memory
              </button>
            </div>
          )}
          {activeStep === 'recall' && (
            <div className="space-y-4">
              <h3 className="section-title"><MagnifyingGlassCircleIcon className="w-5 h-5 text-gray-900" />Recall Context</h3>
              <p className="text-sm text-gray-500">Query across agent sessions — toggle cross-session to recall from all tools.</p>
              <div><label className="block text-xs font-medium text-gray-500 mb-1.5">Query</label><input className="input-dark" placeholder="What did my agent learn about..." value={query} onChange={(e) => setQuery(e.target.value)} /></div>
              <div><label className="block text-xs font-medium text-gray-500 mb-1.5">Max Tokens</label><input type="number" className="input-dark" value={maxTokens} onChange={(e) => setMaxTokens(Number(e.target.value))} /></div>
              <div className="flex items-center justify-between px-3 py-2.5 bg-black/[0.02] rounded-xl border border-black/[0.06]">
                <div>
                  <p className="text-xs font-semibold text-gray-700">Cross-Session &amp; Cross-Tool</p>
                  <p className="text-[10px] text-gray-400">Search across all sessions and AI products</p>
                </div>
                <button
                  onClick={() => setCrossSession(!crossSession)}
                  className={`relative w-10 h-5 rounded-full transition-colors duration-200 ${crossSession ? 'bg-black' : 'bg-gray-300'}`}
                >
                  <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform duration-200 ${crossSession ? 'translate-x-5' : 'translate-x-0.5'}`} />
                </button>
              </div>
              <button onClick={recallContext} disabled={loading || !token || !query.trim()} className="btn-glow w-full flex items-center justify-center gap-2 disabled:opacity-40">
                {loading ? <ArrowPathIcon className="w-4 h-4 animate-spin" /> : <MagnifyingGlassCircleIcon className="w-4 h-4" />}Recall
              </button>
            </div>
          )}
          {activeStep === 'profile' && (
            <div className="space-y-4">
              <h3 className="section-title"><UserCircleIcon className="w-5 h-5 text-gray-900" />Agent Profile</h3>
              <p className="text-sm text-gray-500">Retrieve the agent's memory profile and session history.</p>
              <button onClick={getProfile} disabled={loading || !token} className="btn-glow w-full flex items-center justify-center gap-2 disabled:opacity-40">
                {loading ? <ArrowPathIcon className="w-4 h-4 animate-spin" /> : <UserCircleIcon className="w-4 h-4" />}Get Profile
              </button>
            </div>
          )}
          {activeStep === 'sdk' && (
            <div className="space-y-4">
              <h3 className="section-title"><CodeBracketIcon className="w-5 h-5 text-gray-900" />Agent SDK Examples</h3>
              <p className="text-sm text-gray-500">Attach Membread to any AI framework in 3 lines.</p>
              <div className="flex gap-1 p-1 bg-black/[0.03] rounded-xl">
                {Object.entries(SDK_EXAMPLES).map(([key, ex]) => (
                  <button
                    key={key}
                    onClick={() => setSdkTab(key)}
                    className={`flex-1 px-3 py-1.5 rounded-lg text-[11px] font-semibold transition-all ${
                      sdkTab === key ? 'bg-black text-white' : 'text-gray-500 hover:text-gray-900'
                    }`}
                  >
                    {ex.label}
                  </button>
                ))}
              </div>
              <div className="relative">
                <pre className="text-[11px] font-mono text-gray-600 whitespace-pre-wrap bg-black/[0.02] rounded-xl p-4 border border-black/[0.06] max-h-[320px] overflow-y-auto leading-relaxed">
                  {SDK_EXAMPLES[sdkTab].code}
                </pre>
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(SDK_EXAMPLES[sdkTab].code);
                    setSdkCopied(true);
                    setTimeout(() => setSdkCopied(false), 2000);
                  }}
                  className="absolute top-2 right-2 flex items-center gap-1 px-2 py-1 text-[10px] font-medium text-gray-400 hover:text-gray-900 bg-white/80 backdrop-blur rounded-lg border border-black/[0.06] transition-colors"
                >
                  <ClipboardDocumentIcon className="w-3 h-3" />
                  {sdkCopied ? 'Copied!' : 'Copy'}
                </button>
              </div>
              <div className="px-3 py-2.5 bg-black/[0.02] rounded-xl border border-black/[0.06]">
                <p className="text-[11px] text-gray-500">
                  <strong className="text-gray-700">Works with:</strong> LangChain, LangGraph, CrewAI, AutoGen, LlamaIndex, Cursor, Claude, ChatGPT, and any tool that sends HTTP.
                </p>
              </div>
            </div>
          )}
        </motion.div>

        {/* Right: response panel */}
        <div className="glass-card p-6">
          <h3 className="text-sm font-medium text-gray-500 mb-4">Response</h3>
          <AnimatePresence mode="wait">
            {loading ? (
              <motion.div key="load" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex items-center justify-center py-16">
                <ArrowPathIcon className="w-8 h-8 text-cyan-400 animate-spin" />
              </motion.div>
            ) : result ? (
              <motion.div key="res" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                <div className={`flex items-center gap-2 mb-3 ${result.error ? 'text-red-400' : 'text-green-400'}`}>
                  {result.error ? <ExclamationCircleIcon className="w-5 h-5" /> : <CheckCircleIcon className="w-5 h-5" />}
                  <span className="text-sm font-medium">{result.error ? 'Error' : 'Success'}</span>
                </div>
                <pre className="text-xs font-mono text-gray-500 whitespace-pre-wrap bg-black/[0.02] rounded-xl p-4 border border-black/10 max-h-80 overflow-y-auto">{result.text}</pre>
              </motion.div>
            ) : (
              <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-center py-16 text-gray-400 text-sm">
                Run an action to see the response here.
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
};

export default DemoPage;