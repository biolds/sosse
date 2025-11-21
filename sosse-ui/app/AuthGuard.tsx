"use client";

import { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { Spin } from 'antd';
import { useAuth } from './hooks/useAuth';

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, requiresAuth, isReady } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  const isLoginPage = pathname === '/login' || pathname === '/login/';

  useEffect(() => {
    if (!isReady) return;

    if (requiresAuth && !isAuthenticated && !isLoginPage) {
      router.push(`/login?returnTo=${encodeURIComponent(pathname)}`);
    }
  }, [requiresAuth, isAuthenticated, isReady, pathname, isLoginPage, router]);

  if (!isReady) {
    return <Spin fullscreen tip="Loading..." />;
  }

  if (requiresAuth && !isAuthenticated && !isLoginPage) {
    return <Spin fullscreen tip="Redirecting to login..." />;
  }

  return <>{children}</>;
}
