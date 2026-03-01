import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useApi } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import EmptyState from '../components/EmptyState';
import {
  ChatBubbleLeftRightIcon,
  PaperAirplaneIcon,
  ArrowPathIcon,
  TrashIcon,
  SparklesIcon,
  DocumentTextIcon,
  CpuChipIcon,
  UserIcon,
} from '@heroicons/react/24/outline';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: string[];
  tokenCount?: number;
  compressed?: boolean;
  timestamp: Date;
}

const ChatPage: React.FC = () => {
  const { token } = useAuth();
  const api = useApi();
  const navigate = useNavigate();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [showMeta, setShowMeta] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  // Auto-resize textarea
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
  };

  const sendMessage = async () => {
    if (!token || !input.trim() || loading) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    // Reset textarea height
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
    }

    try {
      const resp = await api.post(
        '/api/memory/recall',
        { query: userMsg.content },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      const assistantMsg: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: resp.data.context || 'No relevant memories found.',
        sources: resp.data.sources || [],
        tokenCount: resp.data.token_count,
        compressed: resp.data.compressed,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (e: any) {
      const errorMsg: ChatMessage = {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: `Error: ${e.response?.data?.detail || e.message}`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const clearChat = () => {
    setMessages([]);
    setShowMeta(null);
  };

  if (!token) {
    return (
      <EmptyState
        icon={ChatBubbleLeftRightIcon}
        title="Agent Chat"
        description="Authenticate to have session-persistent conversations powered by agent memory."
        action={{ label: 'Go to Playground', onClick: () => navigate('/demo') }}
      />
    );
  }

  return (
    <div className="max-w-3xl mx-auto flex flex-col" style={{ height: 'calc(100vh - 160px)' }}>
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-4 flex items-center justify-between"
      >
        <div>
          <div className="flex items-center gap-3 mb-1">
            <ChatBubbleLeftRightIcon className="w-6 h-6 text-gray-900" />
            <h1 className="text-2xl font-extrabold text-gray-900 tracking-tight">
              Agent Chat
            </h1>
          </div>
          <p className="text-sm text-gray-400 ml-9">
            Ask questions — answers are grounded in <strong className="text-gray-600">cross-session agent memory</strong>.
          </p>
        </div>
        {messages.length > 0 && (
          <button
            onClick={clearChat}
            className="flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-medium text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-xl transition-colors"
          >
            <TrashIcon className="w-3.5 h-3.5" />
            Clear
          </button>
        )}
      </motion.div>

      {/* Chat area */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto space-y-4 pb-4 pr-1 scrollbar-thin"
      >
        {/* Welcome state */}
        {messages.length === 0 && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="flex flex-col items-center justify-center h-full text-center"
          >
            <div className="w-16 h-16 rounded-2xl bg-black/[0.03] flex items-center justify-center mb-4">
              <SparklesIcon className="w-8 h-8 text-gray-300" />
            </div>
            <h3 className="text-sm font-bold text-gray-900 mb-1">
              Ask anything across agent sessions
            </h3>
            <p className="text-xs text-gray-400 max-w-sm mb-6">
              Your questions are processed through cross-session semantic recall. The engine
              finds relevant memories from all agents and sessions, returning contextual answers.
            </p>
            <div className="flex flex-wrap justify-center gap-2">
              {[
                'What did my coding agent learn yesterday?',
                'Summarize all agent sessions for Project Phoenix',
                'What context carried from Claude to Cursor?',
                'Show cross-tool memory continuity',
              ].map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => {
                    setInput(suggestion);
                    inputRef.current?.focus();
                  }}
                  className="px-3 py-1.5 text-[11px] font-medium text-gray-500 bg-black/[0.03] border border-black/[0.06] rounded-xl hover:bg-black/[0.06] hover:text-gray-700 transition-colors"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </motion.div>
        )}

        {/* Messages */}
        <AnimatePresence>
          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25 }}
              className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {/* Assistant avatar */}
              {msg.role === 'assistant' && (
                <div className="shrink-0 w-8 h-8 rounded-xl bg-black flex items-center justify-center mt-0.5">
                  <CpuChipIcon className="w-4 h-4 text-white" />
                </div>
              )}

              <div
                className={`max-w-[80%] ${
                  msg.role === 'user'
                    ? 'bg-black text-white rounded-2xl rounded-br-md px-4 py-3'
                    : 'glass-card px-4 py-3'
                }`}
              >
                <p
                  className={`text-sm leading-relaxed whitespace-pre-wrap ${
                    msg.role === 'user' ? 'text-white' : 'text-gray-700'
                  }`}
                >
                  {msg.content}
                </p>

                {/* Metadata for assistant messages */}
                {msg.role === 'assistant' && (msg.sources?.length || msg.tokenCount) && (
                  <div className="mt-2 pt-2 border-t border-black/[0.04]">
                    <button
                      onClick={() =>
                        setShowMeta(showMeta === msg.id ? null : msg.id)
                      }
                      className="text-[10px] font-medium text-gray-400 hover:text-gray-600 transition-colors"
                    >
                      {showMeta === msg.id ? 'Hide details' : 'Show details'}
                    </button>

                    <AnimatePresence>
                      {showMeta === msg.id && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          className="overflow-hidden"
                        >
                          <div className="mt-2 flex flex-wrap items-center gap-2">
                            {msg.tokenCount !== undefined && (
                              <span className="flex items-center gap-1 text-[10px] text-gray-400 bg-black/[0.03] px-2 py-0.5 rounded-lg">
                                <DocumentTextIcon className="w-3 h-3" />
                                {msg.tokenCount} tokens
                              </span>
                            )}
                            {msg.compressed && (
                              <span className="text-[10px] text-violet-500 bg-violet-50 px-2 py-0.5 rounded-lg font-medium">
                                Compressed
                              </span>
                            )}
                          </div>
                          {msg.sources && msg.sources.length > 0 && (
                            <div className="mt-1.5">
                              <p className="text-[10px] font-medium text-gray-400 mb-1">Sources:</p>
                              <div className="flex flex-wrap gap-1">
                                {msg.sources.map((src, i) => (
                                  <span
                                    key={i}
                                    className="text-[10px] font-mono text-gray-500 bg-black/[0.03] px-2 py-0.5 rounded-lg truncate max-w-[160px]"
                                  >
                                    {src}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                )}

                {/* Timestamp */}
                <p
                  className={`text-[10px] mt-1.5 ${
                    msg.role === 'user' ? 'text-white/40' : 'text-gray-300'
                  }`}
                >
                  {msg.timestamp.toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </p>
              </div>

              {/* User avatar */}
              {msg.role === 'user' && (
                <div className="shrink-0 w-8 h-8 rounded-xl bg-gradient-to-br from-gray-900 to-gray-700 flex items-center justify-center mt-0.5">
                  <UserIcon className="w-4 h-4 text-white" />
                </div>
              )}
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Loading indicator */}
        {loading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex gap-3"
          >
            <div className="shrink-0 w-8 h-8 rounded-xl bg-black flex items-center justify-center">
              <CpuChipIcon className="w-4 h-4 text-white" />
            </div>
            <div className="glass-card px-4 py-3">
              <div className="flex items-center gap-2">
                <ArrowPathIcon className="w-4 h-4 text-gray-400 animate-spin" />
                <span className="text-sm text-gray-400">Searching agent memory...</span>
              </div>
            </div>
          </motion.div>
        )}
      </div>

      {/* Input area */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="glass-card p-3 mt-2"
      >
        <div className="flex items-end gap-3">
          <textarea
            ref={inputRef}
            value={input}
            onChange={handleInputChange}
            onKeyDown={onKeyDown}
            placeholder="Ask about agent sessions, cross-tool context..."
            rows={1}
            className="flex-1 resize-none bg-transparent text-sm text-gray-900 placeholder-gray-400 focus:outline-none py-2 px-1 max-h-[120px]"
          />
          <button
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            className="btn-glow flex items-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
          >
            {loading ? (
              <ArrowPathIcon className="w-4 h-4 animate-spin" />
            ) : (
              <PaperAirplaneIcon className="w-4 h-4" />
            )}
            <span className="text-sm">Send</span>
          </button>
        </div>
        <div className="flex items-center justify-between mt-2 px-1">
          <span className="text-[10px] text-gray-300">
            Shift+Enter for new line
          </span>
          <span className="text-[10px] text-gray-300">
            Powered by cross-session agent recall
          </span>
        </div>
      </motion.div>
    </div>
  );
};

export default ChatPage;
