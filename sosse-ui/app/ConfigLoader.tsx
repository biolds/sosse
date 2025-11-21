"use client";

import { useEffect } from 'react';
import { useAppStore } from './useAppStore';

export default function ConfigLoader({ children }: { children: React.ReactNode }) {
  const loadServerConfig = useAppStore((state) => state.loadServerConfig);

  useEffect(() => {
    loadServerConfig();
  }, [loadServerConfig]);

  return <>{children}</>;
}
