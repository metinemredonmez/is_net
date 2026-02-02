/**
 * IOSP Chat Service
 * Chat API calls
 */
import api from './api';

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  sources?: Source[];
  confidence?: number;
  is_helpful?: boolean | null;
  response_time_ms?: number;
  created_at: string;
}

export interface Source {
  content: string;
  document_id?: string;
  document_title?: string;
  chunk_index?: number;
  relevance?: number;
}

export interface Conversation {
  id: string;
  title: string;
  is_active: boolean;
  message_count: number;
  messages?: Message[];
  created_at: string;
  updated_at: string;
}

export interface AskResponse {
  message: Message;
  user_message: Message;
}

export const chatService = {
  /**
   * Get all conversations for current user
   */
  async getConversations(): Promise<Conversation[]> {
    const response = await api.get<Conversation[]>('/chat/conversations/');
    return response.data;
  },

  /**
   * Get single conversation with messages
   */
  async getConversation(id: string): Promise<Conversation> {
    const response = await api.get<Conversation>(`/chat/conversations/${id}/`);
    return response.data;
  },

  /**
   * Create new conversation
   */
  async createConversation(title?: string): Promise<Conversation> {
    const response = await api.post<Conversation>('/chat/conversations/', {
      title: title || '',
    });
    return response.data;
  },

  /**
   * Delete conversation
   */
  async deleteConversation(id: string): Promise<void> {
    await api.delete(`/chat/conversations/${id}/`);
  },

  /**
   * Get messages for a conversation
   */
  async getMessages(conversationId: string): Promise<Message[]> {
    const response = await api.get<Message[]>(
      `/chat/conversations/${conversationId}/messages/`
    );
    return response.data;
  },

  /**
   * Ask a question (send message and get AI response)
   */
  async askQuestion(conversationId: string, question: string): Promise<AskResponse> {
    const response = await api.post<AskResponse>(
      `/chat/conversations/${conversationId}/ask/`,
      { question }
    );
    return response.data;
  },

  /**
   * Submit feedback for a message
   */
  async submitFeedback(
    messageId: string,
    isHelpful: boolean,
    feedback?: string
  ): Promise<void> {
    await api.post(`/chat/messages/${messageId}/feedback/`, {
      is_helpful: isHelpful,
      feedback: feedback || '',
    });
  },
};
