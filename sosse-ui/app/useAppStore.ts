import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import axios from 'axios';

interface AppState {
  isDarkMode: boolean;
  toggleDarkMode: () => void;
  linkMode: "source" | "archive";
  toggleLinkMode: () => void;
  viewMode: "list" | "card";
  setViewMode: (mode: "list" | "card") => void;
  accessToken: string | null;
  refreshToken: string | null;
  username: string | null;
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => void;
  refreshAccessToken: () => Promise<boolean>;
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      isDarkMode: false,
      toggleDarkMode: () => set((state) => ({ isDarkMode: !state.isDarkMode })),

      linkMode: "source",
      toggleLinkMode: () => set((state) => ({
        linkMode: state.linkMode === "source" ? "archive" : "source"
      })),

      viewMode: "list",
      setViewMode: (mode) => set({ viewMode: mode }),

      accessToken: null,
      refreshToken: null,
      username: null,

      login: async (username: string, password: string) => {
        try {
          const response = await axios.post('/api/token/', {
            username,
            password
          });

          set({
            accessToken: response.data.access,
            refreshToken: response.data.refresh,
            username: username
          });

          return true;
        } catch (error) {
          console.error('Login failed:', error);
          return false;
        }
      },

      logout: () => {
        set({
          accessToken: null,
          refreshToken: null,
          username: null
        });
      },

      refreshAccessToken: async () => {
        const { refreshToken } = get();
        if (!refreshToken) return false;

        try {
          const response = await axios.post('/api/token/refresh/', {
            refresh: refreshToken
          });

          set({ accessToken: response.data.access });
          return true;
        } catch (error) {
          console.error('Token refresh failed:', error);
          get().logout();
          return false;
        }
      },
    }),
    {
      name: 'sosse-app-storage',
      partialize: (state) => ({
        isDarkMode: state.isDarkMode,
        linkMode: state.linkMode,
        viewMode: state.viewMode,
      }),
    }
  )
);
