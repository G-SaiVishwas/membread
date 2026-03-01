import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  CodeBracketIcon,
  CubeIcon,
  WrenchScrewdriverIcon,
  ArrowDownTrayIcon,
  ArrowTopRightOnSquareIcon,
  PaperAirplaneIcon,
  CommandLineIcon,
  ServerIcon,
} from '@heroicons/react/24/outline';

interface PluginDef {
  id: string;
  icon: React.FC<{ className?: string }>;
  name: string;
  description: string;
  installCmd: string;
  docsUrl: string;
}

const plugins: PluginDef[] = [
  {
    id: 'mcp-server',
    icon: ServerIcon,
    name: 'MCP Server',
    description:
      'Model Context Protocol server for Claude Code, Cursor, Windsurf, and VS Code Copilot. Auto-attaches memory to every session.',
    installCmd: 'python -m src.mcp_server.server',
    docsUrl: '#',
  },
  {
    id: 'python-sdk',
    icon: CodeBracketIcon,
    name: 'Python SDK',
    description:
      'Core Python SDK with LangChain, CrewAI, AutoGen, and OpenAI integrations. pip install and go.',
    installCmd: 'pip install -e ./sdk',
    docsUrl: '#',
  },
  {
    id: 'browser-ext',
    icon: CubeIcon,
    name: 'Browser Extension',
    description:
      'Captures conversations from ChatGPT, Claude, Gemini, Perplexity, and Microsoft Copilot.',
    installCmd: 'chrome://extensions → Load unpacked → browser_extension/',
    docsUrl: '#',
  },
];

type TerminalLine = { type: 'command' | 'muted' | 'output'; text: string };
interface ChatMsg {
  role: 'user' | 'bot';
  text: string;
}

const terminalContentMap: Record<string, TerminalLine[]> = {
  'mcp-server': [
    { type: 'command', text: '$ python -m src.mcp_server.server' },
    { type: 'muted', text: '> MCP server starting...' },
    { type: 'muted', text: '> Registered tools: store_memory, recall_memory, search_graph' },
    { type: 'output', text: '' },
    { type: 'output', text: 'MCP server ready. Add to your MCP config:' },
    { type: 'output', text: '  "membread": { "command": "python", "args": ["-m", "src.mcp_server.server"] }' },
  ],
  'python-sdk': [
    { type: 'command', text: '$ python' },
    { type: 'command', text: '>>> from membread import MembreadClient' },
    { type: 'command', text: '>>> client = MembreadClient(token="eyJ...")' },
    { type: 'command', text: '>>> client.store("User prefers dark mode", source="my-agent")' },
    { type: 'output', text: "{'observation_id': 'abc-123', 'nodes_created': 1}" },
    { type: 'command', text: '>>> client.recall("user preferences")' },
    { type: 'output', text: "{'context': 'User prefers dark mode', 'cross_tool': False}" },
  ],
};

const chatMessages: ChatMsg[] = [
  {
    role: 'user',
    text: 'How does the browser extension capture ChatGPT conversations?',
  },
  {
    role: 'bot',
    text: 'The extension uses a MutationObserver on the ChatGPT DOM to detect new messages. When a conversation turn completes, it extracts the text and POSTs to /api/capture with source="chatgpt". All captured data flows into the central knowledge base alongside your SDK and MCP data.',
  },
];

const PluginsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('mcp-server');
  const activeIndex = plugins.findIndex((p) => p.id === activeTab);

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-6"
      >
        <div className="flex items-center gap-3 mb-1">
          <CommandLineIcon className="w-6 h-6 text-gray-900" />
          <h1 className="text-2xl font-extrabold text-gray-900 tracking-tight">
            Plugins
          </h1>
        </div>
        <p className="text-sm text-gray-400 ml-9">
          Connect external tools to enhance your{' '}
          <strong className="text-gray-600">agentic memory</strong> workflow.
        </p>
      </motion.div>

      {/* Section: See it in action */}
      <motion.h2
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.05 }}
        className="text-lg font-bold text-gray-900 mb-4"
      >
        See it in action
      </motion.h2>

      {/* Tab bar */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.08 }}
        className="flex gap-1 mb-0"
      >
        {plugins.map((p) => (
          <button
            key={p.id}
            onClick={() => setActiveTab(p.id)}
            className={`px-5 py-2.5 rounded-t-xl text-[13px] font-semibold transition-all duration-200 ${
              activeTab === p.id
                ? 'bg-gray-950 text-white'
                : 'text-gray-400 hover:text-gray-700 bg-black/[0.02]'
            }`}
          >
            {p.name}
          </button>
        ))}
      </motion.div>

      {/* Terminal / Chat mockup */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="bg-gray-950 rounded-b-2xl rounded-tr-2xl border border-gray-800 mb-4 overflow-hidden"
      >
        {/* Title bar */}
        <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-800">
          <div className="w-3 h-3 rounded-full bg-red-500/80" />
          <div className="w-3 h-3 rounded-full bg-yellow-500/80" />
          <div className="w-3 h-3 rounded-full bg-green-500/80" />
          <span className="ml-2 text-xs text-gray-500">
            {activeTab === 'browser-ext' ? 'How It Works' : 'Terminal'}
          </span>
        </div>

        {/* Content */}
        <AnimatePresence mode="wait">
          {activeTab === 'browser-ext' ? (
            /* Chat UI for Browser Extension demo */
            <motion.div
              key="chat"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
              className="p-5 space-y-4 min-h-[180px]"
            >
              {chatMessages.map((msg, i) => (
                <div
                  key={i}
                  className={`flex ${
                    msg.role === 'user' ? 'justify-end' : 'justify-start'
                  }`}
                >
                  <div
                    className={`max-w-[80%] px-4 py-3 rounded-2xl text-sm leading-relaxed ${
                      msg.role === 'user'
                        ? 'bg-blue-600 text-white rounded-br-md'
                        : 'bg-gray-800 text-gray-300 rounded-bl-md'
                    }`}
                  >
                    {msg.text}
                  </div>
                </div>
              ))}
              {/* Input */}
              <div className="flex items-center gap-2 mt-2 bg-gray-800/60 border border-gray-700 rounded-xl px-3 py-2">
                <input
                  type="text"
                  readOnly
                  placeholder="Ask about Membread..."
                  className="flex-1 bg-transparent text-sm text-gray-400 outline-none placeholder-gray-600"
                />
                <PaperAirplaneIcon className="w-4 h-4 text-gray-600" />
              </div>
            </motion.div>
          ) : (
            /* Terminal UI for Claude Code / OpenCode */
            <motion.div
              key={activeTab}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
              className="p-5 font-mono text-sm leading-relaxed min-h-[180px]"
            >
              {(terminalContentMap[activeTab] || []).map((line, i) => (
                <p
                  key={i}
                  className={
                    line.type === 'command'
                      ? 'text-green-400'
                      : line.type === 'muted'
                      ? 'text-gray-500'
                      : 'text-gray-300'
                  }
                >
                  {line.text || '\u00A0'}
                </p>
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      {/* Pagination dots */}
      <div className="flex justify-center gap-2 mb-8">
        {plugins.map((_, i) => (
          <button
            key={i}
            onClick={() => setActiveTab(plugins[i].id)}
            className={`w-2 h-2 rounded-full transition-all duration-200 ${
              i === activeIndex ? 'bg-black scale-125' : 'bg-black/20'
            }`}
          />
        ))}
      </div>

      {/* Plugin cards */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
        className="grid grid-cols-1 sm:grid-cols-3 gap-4"
      >
        {plugins.map((p) => (
          <div
            key={p.id}
            className="bg-white border border-black/[0.06] rounded-2xl p-5 hover:border-black/[0.12] hover:shadow-sm transition-all group"
          >
            <div className="w-10 h-10 rounded-xl bg-black/[0.03] flex items-center justify-center mb-4">
              <p.icon className="w-5 h-5 text-gray-500 group-hover:text-gray-900 transition-colors" />
            </div>
            <h3 className="text-sm font-semibold text-gray-900 mb-1.5">
              {p.name}
            </h3>
            <p className="text-xs text-gray-400 leading-relaxed line-clamp-2 mb-4">
              {p.description}
            </p>
            {/* Install cmd */}
            <div className="bg-gray-950 rounded-lg px-3 py-2 mb-3">
              <code className="text-[11px] text-gray-400 select-all">
                {p.installCmd}
              </code>
            </div>
            {/* Action buttons */}
            <div className="flex gap-2">
              <button
                onClick={() => setActiveTab(p.id)}
                className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-[11px] font-semibold text-gray-700 bg-white border border-black/[0.10] rounded-xl hover:bg-black hover:text-white hover:border-black transition-all duration-200"
              >
                <ArrowDownTrayIcon className="w-3.5 h-3.5" />
                Install
              </button>
              <a
                href={p.docsUrl}
                className="flex items-center justify-center gap-1 px-3 py-2 text-[11px] font-semibold text-gray-400 hover:text-gray-700 transition-colors"
              >
                Docs
                <ArrowTopRightOnSquareIcon className="w-3 h-3" />
              </a>
            </div>
          </div>
        ))}
      </motion.div>

      {/* Bottom hint */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
        className="mt-8 text-center"
      >
        <p className="text-[11px] text-gray-400">
          Build your own plugin with the{' '}
          <a
            href="/demo"
            className="font-semibold text-gray-600 hover:text-gray-900 underline underline-offset-2"
          >
            MCP Server SDK
          </a>
        </p>
      </motion.div>
    </div>
  );
};

export default PluginsPage;
