import axios from 'axios';
import { useAuth } from '../context/AuthContext';

const baseURL = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

export const useApi = () => {
  const { token } = useAuth();

  const instance = axios.create({
    baseURL,
    headers: {
      Authorization: token ? `Bearer ${token}` : undefined,
      'Content-Type': 'application/json',
    },
  });

  return instance;
};
