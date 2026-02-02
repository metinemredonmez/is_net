/**
 * IOSP Auth Service
 * Authentication API calls
 */
import api, { setTokens, clearTokens, getRefreshToken } from './api';
import type {
  User,
  AuthTokens,
  LoginCredentials,
  RegisterData,
} from '@/types';

export const authService = {
  /**
   * Login with email and password
   */
  async login(credentials: LoginCredentials): Promise<{ user: User; tokens: AuthTokens }> {
    // Get tokens
    const tokenResponse = await api.post<AuthTokens>('/auth/token/', credentials);
    const { access, refresh } = tokenResponse.data;

    // Store tokens
    setTokens(access, refresh);

    // Get user info
    const userResponse = await api.get<User>('/auth/me/');

    return {
      user: userResponse.data,
      tokens: { access, refresh },
    };
  },

  /**
   * Register new user
   */
  async register(data: RegisterData): Promise<{ user: User; tokens: AuthTokens }> {
    const response = await api.post<{
      user: User;
      tokens: AuthTokens;
      message: string;
    }>('/auth/register/', data);

    const { tokens, user } = response.data;

    // Store tokens
    setTokens(tokens.access, tokens.refresh);

    return { user, tokens };
  },

  /**
   * Logout user
   */
  async logout(): Promise<void> {
    const refreshToken = getRefreshToken();

    if (refreshToken) {
      try {
        await api.post('/auth/logout/', { refresh: refreshToken });
      } catch {
        // Ignore errors on logout
      }
    }

    clearTokens();
  },

  /**
   * Get current user info
   */
  async getCurrentUser(): Promise<User> {
    const response = await api.get<User>('/auth/me/');
    return response.data;
  },

  /**
   * Change password
   */
  async changePassword(data: {
    old_password: string;
    new_password: string;
    new_password_confirm: string;
  }): Promise<{ tokens: AuthTokens }> {
    const response = await api.post<{
      message: string;
      tokens: AuthTokens;
    }>('/auth/password/change/', data);

    const { tokens } = response.data;
    setTokens(tokens.access, tokens.refresh);

    return { tokens };
  },

  /**
   * Request password reset
   */
  async requestPasswordReset(email: string): Promise<void> {
    await api.post('/auth/password/reset/', { email });
  },

  /**
   * Confirm password reset
   */
  async confirmPasswordReset(data: {
    token: string;
    new_password: string;
    new_password_confirm: string;
  }): Promise<void> {
    await api.post('/auth/password/reset/confirm/', data);
  },
};
