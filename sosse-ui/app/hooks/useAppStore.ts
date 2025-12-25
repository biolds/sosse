import { create } from "zustand";
import { persist } from "zustand/middleware";
import axios from "axios";
import type { Document } from "@/app/types/document";

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

export type SearchTab = "home" | "search" | "images" | "audio" | "video";

export interface Link {
  id: number;
  text: string | null;
  pos: number;
  link_no: number;
  screen_pos: string | null;
  in_nav: boolean;
  url: string;
  title: string | null;
  available: boolean;
}

interface AppState {
  isDarkMode: boolean;
  toggleDarkMode: () => void;
  linkMode: "source" | "archive";
  toggleLinkMode: () => void;
  viewMode: "list" | "card";
  setViewMode: (mode: "list" | "card") => void;
  homeViewMode: "card";
  activeTab: SearchTab;
  setActiveTab: (tab: SearchTab) => void;
  accessToken: string | null;
  username: string | null;
  isInitialized: boolean;
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => void;
  refreshAccessToken: () => Promise<boolean>;
  initializeAuth: () => Promise<void>;
  searchFilters: SearchFilters;
  updateSearchFilters: (filters: SearchFilters) => void;
  collections: Array<{ id: number; name: string }>;
  setCollections: (collections: Array<{ id: number; name: string }>) => void;
  loadCollections: () => Promise<void>;
  isFloatHeaderFolded: boolean;
  toggleFloatHeader: () => void;
  crawlQueueRefreshInterval: number;
  setCrawlQueueRefreshInterval: (interval: number) => void;
  sosseDocument: Document | null;
  setSosseDocument: (document: Document | null) => void;
  documentLinks: Link[];
  setDocumentLinks: (links: Link[]) => void;
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

      homeViewMode: "card",

      activeTab: "home",
      setActiveTab: (tab) => set({ activeTab: tab }),

      searchFilters: {
        lang: "",
        include_hidden: false,
        sort: "-rank",
        adv_params: [],
      },

      updateSearchFilters: (filters) =>
        set({
          searchFilters: filters,
        }),

      collections: [],
      setCollections: (collections) => set({ collections }),
      loadCollections: async () => {
        try {
          const response = await axios.get("/api/collection/");
          set({ collections: response.data.results || response.data || [] });
        } catch (error) {
          console.error("Failed to load collections:", error);
        }
      },

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

      isFloatHeaderFolded: true,
      toggleFloatHeader: () =>
        set((state) => ({ isFloatHeaderFolded: !state.isFloatHeaderFolded })),

      crawlQueueRefreshInterval: 5000,
      setCrawlQueueRefreshInterval: (interval) =>
        set({ crawlQueueRefreshInterval: interval }),

      sosseDocument: null,
      setSosseDocument: (document) => set({ sosseDocument: document }),

      documentLinks: [],
      setDocumentLinks: (links) => set({ documentLinks: links }),
    }),
    {
      name: "sosse-app-storage",
      partialize: (state) => ({
        isDarkMode: state.isDarkMode,
        linkMode: state.linkMode,
        viewMode: state.viewMode,
        crawlQueueRefreshInterval: state.crawlQueueRefreshInterval,
      }),
    },
  ),
);
