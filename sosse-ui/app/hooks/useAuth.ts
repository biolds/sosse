import { useAppStore } from "../useAppStore";
import { useEffect, useState } from "react";

export function useAuth() {
  const { username, accessToken, isInitialized, initializeAuth } =
    useAppStore();
  const [requiresAuth, setRequiresAuth] = useState<boolean | null>(null);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    const init = async () => {
      // First, initialize auth if needed
      if (!isInitialized) {
        await initializeAuth();
      }

      // Then check config and mark as ready
      if (typeof window !== "undefined" && window.sosseConfig) {
        setRequiresAuth(!window.sosseConfig.anonymousSearch);
      }

      // Only set ready after initialization is complete
      setIsReady(true);
    };

    init();

    // Fallback timer in case config is slow to load
    const timer = setTimeout(() => {
      if (typeof window !== "undefined" && window.sosseConfig) {
        setRequiresAuth(!window.sosseConfig.anonymousSearch);
      }
    }, 100);

    return () => clearTimeout(timer);
  }, [isInitialized, initializeAuth]);

  return {
    isAuthenticated: !!accessToken,
    username,
    requiresAuth,
    isReady: isReady && isInitialized,
  };
}
