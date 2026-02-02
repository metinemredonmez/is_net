/**
 * IOSP Frontend Type Definitions
 */

// ===========================================
// User & Auth Types
// ===========================================

export interface User {
  id: string;
  email: string;
  full_name: string;
  phone?: string;
  role: UserRole;
  department?: Department;
  is_active: boolean;
  last_login?: string;
  created_at: string;
}

export type UserRole = 'admin' | 'manager' | 'analyst' | 'operator' | 'viewer';

export interface Department {
  id: string;
  name: string;
  code: string;
}

export interface AuthTokens {
  access: string;
  refresh: string;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  email: string;
  full_name: string;
  phone?: string;
  password: string;
  password_confirm: string;
}

// ===========================================
// Document Types
// ===========================================

export interface Document {
  id: string;
  title: string;
  description?: string;
  file: string;
  file_type: DocumentFileType;
  file_size: number;
  category?: DocumentCategory;
  tags: string[];
  status: DocumentStatus;
  processing_progress: number;
  chunk_count: number;
  is_public: boolean;
  uploaded_by_name?: string;
  task_id?: string;
  created_at: string;
  processed_at?: string;
}

export type DocumentFileType = 'pdf' | 'docx' | 'txt' | 'md';
export type DocumentStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface DocumentCategory {
  id: string;
  name: string;
  slug: string;
  description?: string;
  icon: string;
  color: string;
}

export interface DocumentUploadData {
  title: string;
  description?: string;
  file: File;
  category_id?: string;
  is_public?: boolean;
}

export interface DocumentProcessingStatus {
  id: string;
  title: string;
  status: DocumentStatus;
  processing_progress: number;
  chunk_count: number;
  error_message?: string;
  task_id?: string;
  created_at: string;
  processed_at?: string;
}

// ===========================================
// API Response Types
// ===========================================

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface ApiError {
  detail?: string;
  error?: string;
  message?: string;
  [key: string]: unknown;
}

// ===========================================
// Dashboard Types
// ===========================================

export interface DashboardStats {
  total_documents: number;
  pending_documents: number;
  processing_documents: number;
  completed_documents: number;
  failed_documents: number;
  total_queries?: number;
}

export interface RecentActivity {
  id: string;
  type: 'upload' | 'query' | 'login' | 'process';
  description: string;
  timestamp: string;
  user?: string;
}
