import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

interface AuthContextType {
  token: string;
  setToken: (token: string) => void;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setTokenState] = useState<string>(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('cmcp_token') || '';
    }
    return '';
  });

  const setToken = (t: string) => {
    setTokenState(t);
    if (typeof window !== 'undefined') {
      localStorage.setItem('cmcp_token', t);
    }
  };

  // Auto-acquire a token on startup if none exists
  useEffect(() => {
    if (!token) {
      axios
        .post(`${API_BASE}/api/auth/token`, {
          tenant_id: 'default',
          user_id: 'browser-user',
        })
        .then((res) => {
          if (res.data?.token) {
            setToken(res.data.token);
          }
        })
        .catch(() => {
          // silently ignore – user can authenticate manually
        });
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return <AuthContext.Provider value={{ token, setToken }}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextType => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
};
