/**
 * IOSP Documents Service
 * Document API calls
 */
import api from './api';
import type {
  Document,
  DocumentCategory,
  DocumentUploadData,
  DocumentProcessingStatus,
  PaginatedResponse,
  DashboardStats,
} from '@/types';

export const documentsService = {
  /**
   * Get paginated list of documents
   */
  async getDocuments(params?: {
    page?: number;
    category?: string;
    status?: string;
    search?: string;
  }): Promise<PaginatedResponse<Document>> {
    const response = await api.get<PaginatedResponse<Document>>('/documents/', {
      params,
    });
    return response.data;
  },

  /**
   * Get single document by ID
   */
  async getDocument(id: string): Promise<Document> {
    const response = await api.get<Document>(`/documents/${id}/`);
    return response.data;
  },

  /**
   * Upload a new document
   */
  async uploadDocument(data: DocumentUploadData): Promise<Document> {
    const formData = new FormData();
    formData.append('title', data.title);
    formData.append('file', data.file);

    if (data.description) {
      formData.append('description', data.description);
    }
    if (data.category_id) {
      formData.append('category_id', data.category_id);
    }
    if (data.is_public !== undefined) {
      formData.append('is_public', String(data.is_public));
    }

    const response = await api.post<Document>('/documents/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  /**
   * Update document
   */
  async updateDocument(
    id: string,
    data: Partial<Pick<Document, 'title' | 'description' | 'is_public'>>
  ): Promise<Document> {
    const response = await api.patch<Document>(`/documents/${id}/`, data);
    return response.data;
  },

  /**
   * Delete document
   */
  async deleteDocument(id: string): Promise<void> {
    await api.delete(`/documents/${id}/`);
  },

  /**
   * Get document processing status
   */
  async getDocumentStatus(id: string): Promise<DocumentProcessingStatus> {
    const response = await api.get<DocumentProcessingStatus>(
      `/documents/${id}/status/`
    );
    return response.data;
  },

  /**
   * Trigger document processing
   */
  async processDocument(id: string): Promise<{ task_id: string }> {
    const response = await api.post<{ task_id: string; message: string }>(
      `/documents/${id}/process/`
    );
    return response.data;
  },

  /**
   * Reprocess failed document
   */
  async reprocessDocument(id: string): Promise<{ task_id: string }> {
    const response = await api.post<{ task_id: string; message: string }>(
      `/documents/${id}/reprocess/`
    );
    return response.data;
  },

  /**
   * Get document categories
   */
  async getCategories(): Promise<DocumentCategory[]> {
    const response = await api.get<DocumentCategory[]>('/documents/categories/');
    return response.data;
  },

  /**
   * Get dashboard statistics
   */
  async getDashboardStats(): Promise<DashboardStats> {
    // This could be a dedicated endpoint or computed from documents
    const response = await api.get<PaginatedResponse<Document>>('/documents/');
    const docs = response.data.results;

    return {
      total_documents: response.data.count,
      pending_documents: docs.filter((d) => d.status === 'pending').length,
      processing_documents: docs.filter((d) => d.status === 'processing').length,
      completed_documents: docs.filter((d) => d.status === 'completed').length,
      failed_documents: docs.filter((d) => d.status === 'failed').length,
    };
  },
};
