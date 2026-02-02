import { create } from 'zustand';
import { chatService, type Conversation, type Message } from '@/services/chat.service';

interface ChatState {
  conversations: Conversation[];
  activeConversation: Conversation | null;
  messages: Message[];
  isLoadingConversations: boolean;
  isLoadingMessages: boolean;
  isSending: boolean;
  error: string | null;
}

interface ChatActions {
  fetchConversations: () => Promise<void>;
  fetchMessages: (conversationId: string) => Promise<void>;
  createConversation: (title?: string) => Promise<Conversation | null>;
  deleteConversation: (id: string) => Promise<boolean>;
  setActiveConversation: (conversation: Conversation | null) => void;
  sendMessage: (question: string) => Promise<boolean>;
  submitFeedback: (messageId: string, isHelpful: boolean) => Promise<boolean>;
  clearError: () => void;
  reset: () => void;
}

const initialState: ChatState = {
  conversations: [],
  activeConversation: null,
  messages: [],
  isLoadingConversations: false,
  isLoadingMessages: false,
  isSending: false,
  error: null,
};

export const useChatStore = create<ChatState & ChatActions>((set, get) => ({
  ...initialState,

  fetchConversations: async () => {
    set({ isLoadingConversations: true, error: null });
    try {
      const conversations = await chatService.getConversations();
      set({ conversations, isLoadingConversations: false });
    } catch (error) {
      set({
        error: 'Sohbetler yüklenirken hata oluştu',
        isLoadingConversations: false,
      });
    }
  },

  fetchMessages: async (conversationId: string) => {
    set({ isLoadingMessages: true, error: null });
    try {
      const messages = await chatService.getMessages(conversationId);
      set({ messages, isLoadingMessages: false });
    } catch (error) {
      set({
        error: 'Mesajlar yüklenirken hata oluştu',
        isLoadingMessages: false,
      });
    }
  },

  createConversation: async (title?: string) => {
    set({ error: null });
    try {
      const conversation = await chatService.createConversation(title);
      set((state) => ({
        conversations: [conversation, ...state.conversations],
        activeConversation: conversation,
        messages: [],
      }));
      return conversation;
    } catch (error) {
      set({ error: 'Sohbet oluşturulamadı' });
      return null;
    }
  },

  deleteConversation: async (id: string) => {
    try {
      await chatService.deleteConversation(id);
      const { activeConversation } = get();
      set((state) => ({
        conversations: state.conversations.filter((c) => c.id !== id),
        activeConversation: activeConversation?.id === id ? null : activeConversation,
        messages: activeConversation?.id === id ? [] : state.messages,
      }));
      return true;
    } catch (error) {
      set({ error: 'Sohbet silinemedi' });
      return false;
    }
  },

  setActiveConversation: (conversation: Conversation | null) => {
    set({ activeConversation: conversation, messages: [] });
    if (conversation) {
      get().fetchMessages(conversation.id);
    }
  },

  sendMessage: async (question: string) => {
    const { activeConversation } = get();
    if (!activeConversation) return false;

    set({ isSending: true, error: null });

    // Optimistically add user message
    const tempMessage: Message = {
      id: 'temp-' + Date.now(),
      role: 'user',
      content: question,
      created_at: new Date().toISOString(),
    };
    set((state) => ({ messages: [...state.messages, tempMessage] }));

    try {
      const response = await chatService.askQuestion(activeConversation.id, question);

      set((state) => ({
        messages: [
          ...state.messages.filter((m) => !m.id.startsWith('temp-')),
          response.user_message,
          response.message,
        ],
        conversations: state.conversations.map((c) =>
          c.id === activeConversation.id
            ? {
                ...c,
                message_count: c.message_count + 2,
                title: c.title || question.slice(0, 50),
                updated_at: new Date().toISOString(),
              }
            : c
        ),
        isSending: false,
      }));

      return true;
    } catch (error) {
      set((state) => ({
        messages: state.messages.filter((m) => !m.id.startsWith('temp-')),
        error: 'Mesaj gönderilemedi',
        isSending: false,
      }));
      return false;
    }
  },

  submitFeedback: async (messageId: string, isHelpful: boolean) => {
    try {
      await chatService.submitFeedback(messageId, isHelpful);
      set((state) => ({
        messages: state.messages.map((m) =>
          m.id === messageId ? { ...m, is_helpful: isHelpful } : m
        ),
      }));
      return true;
    } catch (error) {
      set({ error: 'Geri bildirim gönderilemedi' });
      return false;
    }
  },

  clearError: () => set({ error: null }),

  reset: () => set(initialState),
}));
