import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import axios from 'axios';

interface ServerConfig {
  [key: string]: unknown;
}

interface AppState {
  isDarkMode: boolean;
  toggleDarkMode: () => void;
  serverConfig: ServerConfig | null;
  isConfigLoaded: boolean;
  loadServerConfig: () => Promise<void>;
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      isDarkMode: false,
      toggleDarkMode: () => set((state) => ({ isDarkMode: !state.isDarkMode })),
      serverConfig: null,
      isConfigLoaded: false,
      loadServerConfig: async () => {
        if (get().isConfigLoaded) return;
        try {
          const response = await axios.get('/api/config/');
          set({ serverConfig: response.data, isConfigLoaded: true });
        } catch (error) {
          console.error('Failed to load server config:', error);
          set({ isConfigLoaded: true });
        }
      },
    }),
    {
      name: 'sosse-app-storage',
      partialize: (state) => ({ isDarkMode: state.isDarkMode }),
    }
  )
);
