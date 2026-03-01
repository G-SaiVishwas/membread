import React, { useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import Dock from './Dock';
import Header from './Header';
import CommandPalette from './CommandPalette';
import { useAuth } from '../context/AuthContext';
import { useLocation } from 'react-router-dom';
import axios from 'axios';

const apiBase = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { token } = useAuth();
  const [apiOk, setApiOk] = useState(true);
  const [cmdOpen, setCmdOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    axios
      .get(`${apiBase}/health`)
      .then(() => setApiOk(true))
      .catch(() => setApiOk(false));
  }, []);

  // Global Cmd+K / Ctrl+K
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setCmdOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-white">
      <Header onOpenCommandPalette={() => setCmdOpen(true)} apiOk={apiOk} />
      <main className="flex-1 overflow-y-auto">
        <div className="px-8 pt-6 pb-28">
          {/* Page content with transition */}
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.15 }}
            >
              {children}
            </motion.div>
          </AnimatePresence>
        </div>
      </main>

      {/* Bottom dock navigation */}
      <Dock />

      {/* Command palette */}
      <CommandPalette open={cmdOpen} onClose={() => setCmdOpen(false)} />
    </div>
  );
};

export default Layout;