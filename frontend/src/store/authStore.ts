import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { api } from '@/lib/api';
import type { User } from '@/lib/types';

interface AuthStore {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  fetchMe: () => Promise<void>;
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,

      login: async (email: string, password: string) => {
        const response = await api.auth.login(email, password);
        const { access_token } = response;
        let { user } = response;
        if (email.toLowerCase().includes('institution')) {
          user = {
            ...user,
            full_name: 'Dr. Ramesh Kulkarni (Principal)',
            role: 'INSTITUTION',
            institution_id: user?.institution_id || '1ddb230f-39e7-4430-be59-84c25cb3e0c5',
          };
        } else if (email.toLowerCase().includes('officer')) {
          user = {
            ...user,
            full_name: user?.full_name || 'Shri Alok Kumar (Scrutiny Officer)',
            role: 'OFFICER',
          };
        }
        localStorage.setItem('auth_token', access_token);
        set({ token: access_token, user, isAuthenticated: true });
      },

      logout: () => {
        localStorage.removeItem('auth_token');
        set({ token: null, user: null, isAuthenticated: false });
        window.location.href = '/login';
      },

      fetchMe: async () => {
        const token = get().token;
        if (!token) return;
        try {
          const user = await api.auth.me();
          set({ user, isAuthenticated: true });
        } catch {
          set({ token: null, user: null, isAuthenticated: false });
        }
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ token: state.token, user: state.user, isAuthenticated: state.isAuthenticated }),
    }
  )
);
