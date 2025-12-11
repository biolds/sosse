import { create } from "zustand";
import { persist } from "zustand/middleware";
import axios from "axios";

export interface AdvancedFilter {
  id?: string;
  type: "inc" | "exc";
  field: string;
  operator: "contain" | "equal" | "regexp";
  term: string;
  case_sensitive: boolean;
}

export interface SearchFilters {
  lang: string;
  collection?: number;
  include_hidden: boolean;
  sort: string;
  adv_params: AdvancedFilter[];
}

interface AppState {
  isDarkMode: boolean;
  toggleDarkMode: () => void;
  linkMode: "source" | "archive";
  toggleLinkMode: () => void;
  viewMode: "list" | "card";
  setViewMode: (mode: "list" | "card") => void;
  accessToken: string | null;
  username: string | null;
  isInitialized: boolean;
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => void;
  refreshAccessToken: () => Promise<boolean>;
  initializeAuth: () => Promise<void>;
  searchFilters: SearchFilters;
  updateSearchFilters: (filters: SearchFilters) => void;
  addFilter: () => void;
  removeFilter: (index: number) => void;
  updateFilter: (
    index: number,
    field: keyof AdvancedFilter,
    value: string | boolean,
  ) => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      isDarkMode: false,
      toggleDarkMode: () => set((state) => ({ isDarkMode: !state.isDarkMode })),

      linkMode: "source",
      toggleLinkMode: () =>
        set((state) => ({
          linkMode: state.linkMode === "source" ? "archive" : "source",
        })),

      viewMode: "list",
      setViewMode: (mode) => set({ viewMode: mode }),

      searchFilters: {
        lang: "en",
        include_hidden: false,
        sort: "-rank",
        adv_params: [],
      },

      updateSearchFilters: (filters) =>
        set({
          filters,
        }),

      addFilter: () =>
        set((state) => ({
          searchFilters: {
            ...state.searchFilters,
            adv_params: [
              ...state.searchFilters.adv_params,
              {
                id: `filter-${Date.now()}-${Math.random()}`,
                type: "inc",
                field: "doc",
                operator: "contain",
                term: "",
                case_sensitive: false,
              },
            ],
          },
        })),

      removeFilter: (index) =>
        set((state) => ({
          searchFilters: {
            ...state.searchFilters,
            adv_params: state.searchFilters.adv_params.filter(
              (_, i) => i !== index,
            ),
          },
        })),

      updateFilter: (index, field, value) =>
        set((state) => ({
          searchFilters: {
            ...state.searchFilters,
            adv_params: state.searchFilters.adv_params.map((filter, i) =>
              i === index ? { ...filter, [field]: value } : filter,
            ),
          },
        })),

      accessToken: null,
      username: null,
      isInitialized: false,

      initializeAuth: async () => {
        try {
          const response = await axios.post(
            "/api/token/refresh/",
            {},
            {
              withCredentials: true,
            },
          );

          if (response.data.access) {
            // Fetch user profile to get username
            try {
              const profileResponse = await axios.get("/api/profile/", {
                headers: { Authorization: `Bearer ${response.data.access}` },
                withCredentials: true,
              });

              set({
                accessToken: response.data.access,
                username: profileResponse.data.username,
                isInitialized: true,
              });
            } catch {
              // If profile fetch fails, just set token
              set({
                accessToken: response.data.access,
                isInitialized: true,
              });
            }
          } else {
            set({ isInitialized: true });
          }
        } catch {
          set({ isInitialized: true });
        }
      },

      login: async (username: string, password: string) => {
        try {
          const response = await axios.post(
            "/api/token/",
            {
              username,
              password,
            },
            {
              withCredentials: true,
            },
          );

          set({
            accessToken: response.data.access,
            username: username,
          });

          return true;
        } catch (error) {
          console.error("Login failed:", error);
          return false;
        }
      },

      logout: async () => {
        try {
          await axios.post(
            "/api/token/logout/",
            {},
            {
              withCredentials: true,
            },
          );
        } catch (error) {
          console.error("Logout request failed:", error);
        }

        set({
          accessToken: null,
          username: null,
        });
      },

      refreshAccessToken: async () => {
        try {
          const response = await axios.post(
            "/api/token/refresh/",
            {},
            {
              withCredentials: true,
            },
          );

          set({ accessToken: response.data.access });
          return true;
        } catch (error) {
          console.error("Token refresh failed:", error);
          get().logout();
          return false;
        }
      },
    }),
    {
      name: "sosse-app-storage",
      partialize: (state) => ({
        isDarkMode: state.isDarkMode,
        linkMode: state.linkMode,
        viewMode: state.viewMode,
      }),
    },
  ),
);
