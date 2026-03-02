import { create } from 'zustand';
import { persist } from 'zustand/middleware';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api/v1';

interface UserInfo {
  id: string;
  username: string;
  email: string;
  avatar_url: string | null;
  credits_balance: number;
  created_at: string | null;
}

interface AuthState {
  token: string | null;
  user: UserInfo | null;
  isAuthenticated: boolean;

  login: (username: string, password: string) => Promise<string | null>;
  register: (username: string, email: string, password: string) => Promise<string | null>;
  fetchMe: () => Promise<void>;
  logout: () => void;
  updateCredits: (balance: number) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      user: null,
      isAuthenticated: false,

      login: async (username, password) => {
        try {
          const res = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password }),
          });
          const data = await res.json();
          if (data.success && data.token) {
            set({ token: data.token, user: data.user, isAuthenticated: true });
            return null;
          }
          return data.error || '登录失败';
        } catch {
          return '网络连接失败';
        }
      },

      register: async (username, email, password) => {
        try {
          const res = await fetch(`${API_BASE}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, email, password }),
          });
          const data = await res.json();
          if (data.success && data.token) {
            set({ token: data.token, user: data.user, isAuthenticated: true });
            return null;
          }
          return data.error || '注册失败';
        } catch {
          return '网络连接失败';
        }
      },

      fetchMe: async () => {
        const { token } = get();
        if (!token) return;
        try {
          const res = await fetch(`${API_BASE}/auth/me`, {
            headers: { Authorization: `Bearer ${token}` },
          });
          const data = await res.json();
          if (data.success && data.user) {
            set({ user: data.user, isAuthenticated: true });
          } else {
            set({ token: null, user: null, isAuthenticated: false });
          }
        } catch {
          // silently fail
        }
      },

      logout: () => {
        set({ token: null, user: null, isAuthenticated: false });
      },

      updateCredits: (balance) => {
        const { user } = get();
        if (user) {
          set({ user: { ...user, credits_balance: balance } });
        }
      },
    }),
    {
      name: 'storm-ai-auth',
      partialize: (state) => ({ token: state.token, user: state.user, isAuthenticated: state.isAuthenticated }),
    }
  )
);

export function getAuthHeader(): Record<string, string> {
  const token = useAuthStore.getState().token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}
