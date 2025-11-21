import { useAppStore } from '../useAppStore';
import { useEffect, useState } from 'react';

export function useAuth() {
  const { username, accessToken } = useAppStore();
  const [requiresAuth, setRequiresAuth] = useState<boolean | null>(null);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    const checkConfig = () => {
      if (typeof window !== 'undefined' && window.sosseConfig) {
        setRequiresAuth(!window.sosseConfig.anonymousSearch);
        setIsReady(true);
      }
    };

    checkConfig();

    const timer = setTimeout(checkConfig, 100);

    return () => clearTimeout(timer);
  }, []);

  return {
    isAuthenticated: !!accessToken,
    username,
    requiresAuth,
    isReady
  };
}
