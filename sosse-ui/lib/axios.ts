import axios from "axios";
import { useAppStore } from "@/app/hooks/useAppStore";

let isRedirecting = false;

axios.defaults.withCredentials = true;

axios.interceptors.request.use((config) => {
  const { accessToken } = useAppStore.getState();
  if (accessToken && config.headers) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

axios.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Don't intercept 401 from login/refresh endpoints
    const isAuthEndpoint = originalRequest.url?.includes("/api/token/");

    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !isAuthEndpoint
    ) {
      originalRequest._retry = true;

      const { refreshAccessToken, logout } = useAppStore.getState();

      const refreshed = await refreshAccessToken();

      if (refreshed) {
        const { accessToken } = useAppStore.getState();
        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${accessToken}`;
        }
        return axios(originalRequest);
      } else {
        if (!isRedirecting && typeof window !== "undefined") {
          isRedirecting = true;
          logout();
          const currentPath = window.location.pathname;
          window.location.href = `/login?returnTo=${encodeURIComponent(currentPath)}`;
        }
      }
    }

    return Promise.reject(error);
  },
);

export default axios;
