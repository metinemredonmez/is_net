/**
 * IOSP useAuth Hook
 * Provides auth context and utilities
 */
'use client';

import { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuthStore } from '@/store/auth.store';

interface UseAuthOptions {
  required?: boolean;
  redirectTo?: string;
  allowedRoles?: string[];
}

export function useAuth(options: UseAuthOptions = {}) {
  const {
    required = false,
    redirectTo = '/login',
    allowedRoles,
  } = options;

  const router = useRouter();
  const pathname = usePathname();
  const {
    user,
    isAuthenticated,
    isLoading,
    error,
    login,
    logout,
    register,
    fetchUser,
    clearError,
    checkAuth,
  } = useAuthStore();

  useEffect(() => {
    // Check authentication on mount
    checkAuth();
  }, [checkAuth]);

  useEffect(() => {
    // Skip during loading
    if (isLoading) return;

    // If authentication required but not authenticated
    if (required && !isAuthenticated) {
      // Save intended destination
      const returnUrl = encodeURIComponent(pathname);
      router.push(`${redirectTo}?returnUrl=${returnUrl}`);
      return;
    }

    // If role restriction and user doesn't have required role
    if (required && isAuthenticated && allowedRoles && user) {
      if (!allowedRoles.includes(user.role)) {
        router.push('/unauthorized');
      }
    }
  }, [required, isAuthenticated, isLoading, user, allowedRoles, router, pathname, redirectTo]);

  // Permission helpers
  const isAdmin = user?.role === 'admin';
  const isManager = user?.role === 'manager' || isAdmin;
  const isAnalyst = user?.role === 'analyst' || isManager;
  const canUploadDocuments = ['admin', 'manager', 'analyst', 'operator'].includes(
    user?.role || ''
  );
  const canViewAnalytics = user?.role !== 'viewer';

  return {
    user,
    isAuthenticated,
    isLoading,
    error,
    login,
    logout,
    register,
    fetchUser,
    clearError,

    // Permission helpers
    isAdmin,
    isManager,
    isAnalyst,
    canUploadDocuments,
    canViewAnalytics,
  };
}
