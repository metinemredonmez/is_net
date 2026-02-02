/**
 * Chat Component Tests
 * Tests for chat service and components
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { chatService } from '@/services/chat.service';
import { useChatStore } from '@/store/chat.store';
import api from '@/services/api';

// Mock API
vi.mock('@/services/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

const mockConversation = {
  id: 'conv-1',
  title: 'Test Conversation',
  is_active: true,
  message_count: 2,
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
};

const mockMessage = {
  id: 'msg-1',
  role: 'assistant' as const,
  content: 'This is a test response',
  sources: [
    {
      content: 'Source content',
      document_id: 'doc-1',
      document_title: 'Test Document',
      relevance: 0.95,
    },
  ],
  confidence: 0.9,
  is_helpful: null,
  response_time_ms: 1500,
  created_at: '2025-01-01T00:00:00Z',
};

const mockUserMessage = {
  id: 'msg-0',
  role: 'user' as const,
  content: 'Test question',
  created_at: '2025-01-01T00:00:00Z',
};

describe('Chat Service', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getConversations', () => {
    it('should fetch all conversations', async () => {
      (api.get as any).mockResolvedValueOnce({ data: [mockConversation] });

      const result = await chatService.getConversations();

      expect(api.get).toHaveBeenCalledWith('/chat/conversations/');
      expect(result).toEqual([mockConversation]);
    });

    it('should handle empty conversations', async () => {
      (api.get as any).mockResolvedValueOnce({ data: [] });

      const result = await chatService.getConversations();

      expect(result).toEqual([]);
    });
  });

  describe('getConversation', () => {
    it('should fetch single conversation', async () => {
      const conversationWithMessages = {
        ...mockConversation,
        messages: [mockUserMessage, mockMessage],
      };
      (api.get as any).mockResolvedValueOnce({ data: conversationWithMessages });

      const result = await chatService.getConversation('conv-1');

      expect(api.get).toHaveBeenCalledWith('/chat/conversations/conv-1/');
      expect(result.messages).toHaveLength(2);
    });
  });

  describe('createConversation', () => {
    it('should create new conversation without title', async () => {
      (api.post as any).mockResolvedValueOnce({ data: mockConversation });

      const result = await chatService.createConversation();

      expect(api.post).toHaveBeenCalledWith('/chat/conversations/', { title: '' });
      expect(result).toEqual(mockConversation);
    });

    it('should create new conversation with title', async () => {
      const titled = { ...mockConversation, title: 'Custom Title' };
      (api.post as any).mockResolvedValueOnce({ data: titled });

      const result = await chatService.createConversation('Custom Title');

      expect(api.post).toHaveBeenCalledWith('/chat/conversations/', { title: 'Custom Title' });
      expect(result.title).toBe('Custom Title');
    });
  });

  describe('deleteConversation', () => {
    it('should delete conversation', async () => {
      (api.delete as any).mockResolvedValueOnce({});

      await chatService.deleteConversation('conv-1');

      expect(api.delete).toHaveBeenCalledWith('/chat/conversations/conv-1/');
    });
  });

  describe('getMessages', () => {
    it('should fetch messages for conversation', async () => {
      (api.get as any).mockResolvedValueOnce({ data: [mockUserMessage, mockMessage] });

      const result = await chatService.getMessages('conv-1');

      expect(api.get).toHaveBeenCalledWith('/chat/conversations/conv-1/messages/');
      expect(result).toHaveLength(2);
    });
  });

  describe('askQuestion', () => {
    it('should send question and receive response', async () => {
      const askResponse = {
        message: mockMessage,
        user_message: mockUserMessage,
      };
      (api.post as any).mockResolvedValueOnce({ data: askResponse });

      const result = await chatService.askQuestion('conv-1', 'Test question');

      expect(api.post).toHaveBeenCalledWith('/chat/conversations/conv-1/ask/', {
        question: 'Test question',
      });
      expect(result.message).toEqual(mockMessage);
      expect(result.user_message).toEqual(mockUserMessage);
    });
  });

  describe('submitFeedback', () => {
    it('should submit positive feedback', async () => {
      (api.post as any).mockResolvedValueOnce({});

      await chatService.submitFeedback('msg-1', true);

      expect(api.post).toHaveBeenCalledWith('/chat/messages/msg-1/feedback/', {
        is_helpful: true,
        feedback: '',
      });
    });

    it('should submit negative feedback with comment', async () => {
      (api.post as any).mockResolvedValueOnce({});

      await chatService.submitFeedback('msg-1', false, 'Not accurate');

      expect(api.post).toHaveBeenCalledWith('/chat/messages/msg-1/feedback/', {
        is_helpful: false,
        feedback: 'Not accurate',
      });
    });
  });
});

describe('Chat Store', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useChatStore.getState().reset();
  });

  describe('fetchConversations', () => {
    it('should fetch and store conversations', async () => {
      (api.get as any).mockResolvedValueOnce({ data: [mockConversation] });

      const { result } = renderHook(() => useChatStore());

      await act(async () => {
        await result.current.fetchConversations();
      });

      expect(result.current.conversations).toHaveLength(1);
      expect(result.current.conversations[0].id).toBe('conv-1');
      expect(result.current.isLoadingConversations).toBe(false);
    });

    it('should handle fetch error', async () => {
      (api.get as any).mockRejectedValueOnce(new Error('Network error'));

      const { result } = renderHook(() => useChatStore());

      await act(async () => {
        await result.current.fetchConversations();
      });

      expect(result.current.error).toBe('Sohbetler yüklenirken hata oluştu');
      expect(result.current.isLoadingConversations).toBe(false);
    });
  });

  describe('createConversation', () => {
    it('should create conversation and set as active', async () => {
      (api.post as any).mockResolvedValueOnce({ data: mockConversation });

      const { result } = renderHook(() => useChatStore());

      let newConv;
      await act(async () => {
        newConv = await result.current.createConversation();
      });

      expect(newConv).toEqual(mockConversation);
      expect(result.current.conversations).toContainEqual(mockConversation);
      expect(result.current.activeConversation).toEqual(mockConversation);
    });
  });

  describe('deleteConversation', () => {
    it('should delete conversation and clear if active', async () => {
      (api.post as any).mockResolvedValueOnce({ data: mockConversation });
      (api.delete as any).mockResolvedValueOnce({});

      const { result } = renderHook(() => useChatStore());

      // First create
      await act(async () => {
        await result.current.createConversation();
      });

      expect(result.current.activeConversation?.id).toBe('conv-1');

      // Then delete
      await act(async () => {
        await result.current.deleteConversation('conv-1');
      });

      expect(result.current.conversations).toHaveLength(0);
      expect(result.current.activeConversation).toBeNull();
    });
  });

  describe('sendMessage', () => {
    it('should send message and update state', async () => {
      const askResponse = {
        message: mockMessage,
        user_message: mockUserMessage,
      };
      (api.post as any)
        .mockResolvedValueOnce({ data: mockConversation })
        .mockResolvedValueOnce({ data: askResponse });

      const { result } = renderHook(() => useChatStore());

      // Create conversation first
      await act(async () => {
        await result.current.createConversation();
      });

      // Send message
      let success;
      await act(async () => {
        success = await result.current.sendMessage('Test question');
      });

      expect(success).toBe(true);
      expect(result.current.messages).toContainEqual(mockMessage);
      expect(result.current.messages).toContainEqual(mockUserMessage);
      expect(result.current.isSending).toBe(false);
    });

    it('should not send message without active conversation', async () => {
      const { result } = renderHook(() => useChatStore());

      let success;
      await act(async () => {
        success = await result.current.sendMessage('Test');
      });

      expect(success).toBe(false);
    });
  });

  describe('submitFeedback', () => {
    it('should update message feedback state', async () => {
      (api.post as any)
        .mockResolvedValueOnce({ data: mockConversation })
        .mockResolvedValueOnce({
          data: { message: mockMessage, user_message: mockUserMessage },
        })
        .mockResolvedValueOnce({});

      const { result } = renderHook(() => useChatStore());

      // Setup
      await act(async () => {
        await result.current.createConversation();
        await result.current.sendMessage('Test');
      });

      // Submit feedback
      await act(async () => {
        await result.current.submitFeedback('msg-1', true);
      });

      const updatedMessage = result.current.messages.find((m) => m.id === 'msg-1');
      expect(updatedMessage?.is_helpful).toBe(true);
    });
  });

  describe('setActiveConversation', () => {
    it('should set active conversation and fetch messages', async () => {
      (api.get as any).mockResolvedValueOnce({ data: [mockUserMessage, mockMessage] });

      const { result } = renderHook(() => useChatStore());

      await act(async () => {
        result.current.setActiveConversation(mockConversation);
      });

      expect(result.current.activeConversation).toEqual(mockConversation);
      // Messages should be fetched
      expect(api.get).toHaveBeenCalledWith('/chat/conversations/conv-1/messages/');
    });

    it('should clear messages when setting null', async () => {
      const { result } = renderHook(() => useChatStore());

      act(() => {
        result.current.setActiveConversation(null);
      });

      expect(result.current.activeConversation).toBeNull();
      expect(result.current.messages).toEqual([]);
    });
  });

  describe('reset', () => {
    it('should reset store to initial state', async () => {
      (api.post as any).mockResolvedValueOnce({ data: mockConversation });

      const { result } = renderHook(() => useChatStore());

      await act(async () => {
        await result.current.createConversation();
      });

      expect(result.current.conversations).toHaveLength(1);

      act(() => {
        result.current.reset();
      });

      expect(result.current.conversations).toHaveLength(0);
      expect(result.current.activeConversation).toBeNull();
      expect(result.current.messages).toHaveLength(0);
    });
  });
});

describe('Chat Types', () => {
  it('should have correct message structure', () => {
    expect(mockMessage).toHaveProperty('id');
    expect(mockMessage).toHaveProperty('role');
    expect(mockMessage).toHaveProperty('content');
    expect(mockMessage).toHaveProperty('sources');
    expect(mockMessage).toHaveProperty('confidence');
    expect(mockMessage).toHaveProperty('response_time_ms');
  });

  it('should have correct source structure', () => {
    const source = mockMessage.sources![0];
    expect(source).toHaveProperty('content');
    expect(source).toHaveProperty('document_id');
    expect(source).toHaveProperty('document_title');
    expect(source).toHaveProperty('relevance');
  });

  it('should have correct conversation structure', () => {
    expect(mockConversation).toHaveProperty('id');
    expect(mockConversation).toHaveProperty('title');
    expect(mockConversation).toHaveProperty('is_active');
    expect(mockConversation).toHaveProperty('message_count');
  });
});
