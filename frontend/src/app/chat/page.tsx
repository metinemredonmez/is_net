'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import { chatService, type Conversation, type Message } from '@/services/chat.service';
import { useAuth } from '@/hooks/useAuth';
import {
  MessageSquare,
  Plus,
  Send,
  Trash2,
  Loader2,
  Bot,
  User,
  FileText,
  ThumbsUp,
  ThumbsDown,
  ChevronRight,
  AlertCircle,
  Clock,
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { tr } from 'date-fns/locale';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';

export default function ChatPage() {
  const router = useRouter();
  const { user } = useAuth({ required: true });

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversation, setActiveConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoadingConversations, setIsLoadingConversations] = useState(true);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [isCreating, setIsCreating] = useState(false);

  // Fetch conversations
  const fetchConversations = useCallback(async () => {
    try {
      const data = await chatService.getConversations();
      setConversations(data);
    } catch (error) {
      console.error('Error fetching conversations:', error);
      toast.error('Sohbetler yüklenirken hata oluştu');
    } finally {
      setIsLoadingConversations(false);
    }
  }, []);

  // Fetch messages for active conversation
  const fetchMessages = useCallback(async (conversationId: string) => {
    setIsLoadingMessages(true);
    try {
      const data = await chatService.getMessages(conversationId);
      setMessages(data);
    } catch (error) {
      console.error('Error fetching messages:', error);
      toast.error('Mesajlar yüklenirken hata oluştu');
    } finally {
      setIsLoadingMessages(false);
    }
  }, []);

  useEffect(() => {
    fetchConversations();
  }, [fetchConversations]);

  useEffect(() => {
    if (activeConversation) {
      fetchMessages(activeConversation.id);
    }
  }, [activeConversation, fetchMessages]);

  // Create new conversation
  const handleCreateConversation = async () => {
    setIsCreating(true);
    try {
      const newConversation = await chatService.createConversation();
      setConversations((prev) => [newConversation, ...prev]);
      setActiveConversation(newConversation);
      setMessages([]);
      toast.success('Yeni sohbet oluşturuldu');
    } catch (error) {
      console.error('Error creating conversation:', error);
      toast.error('Sohbet oluşturulamadı');
    } finally {
      setIsCreating(false);
    }
  };

  // Delete conversation
  const handleDeleteConversation = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Bu sohbeti silmek istediğinizden emin misiniz?')) return;

    try {
      await chatService.deleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (activeConversation?.id === id) {
        setActiveConversation(null);
        setMessages([]);
      }
      toast.success('Sohbet silindi');
    } catch (error) {
      console.error('Error deleting conversation:', error);
      toast.error('Sohbet silinemedi');
    }
  };

  // Send message
  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim() || !activeConversation || isSending) return;

    const question = inputMessage.trim();
    setInputMessage('');
    setIsSending(true);

    // Optimistically add user message
    const tempUserMessage: Message = {
      id: 'temp-user',
      role: 'user',
      content: question,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMessage]);

    try {
      const response = await chatService.askQuestion(activeConversation.id, question);

      // Replace temp message with real messages
      setMessages((prev) => [
        ...prev.filter((m) => m.id !== 'temp-user'),
        response.user_message,
        response.message,
      ]);

      // Update conversation in list
      setConversations((prev) =>
        prev.map((c) =>
          c.id === activeConversation.id
            ? { ...c, message_count: c.message_count + 2, updated_at: new Date().toISOString() }
            : c
        )
      );
    } catch (error) {
      console.error('Error sending message:', error);
      toast.error('Mesaj gönderilemedi');
      // Remove temp message on error
      setMessages((prev) => prev.filter((m) => m.id !== 'temp-user'));
      setInputMessage(question);
    } finally {
      setIsSending(false);
    }
  };

  // Submit feedback
  const handleFeedback = async (messageId: string, isHelpful: boolean) => {
    try {
      await chatService.submitFeedback(messageId, isHelpful);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === messageId ? { ...m, is_helpful: isHelpful } : m
        )
      );
      toast.success('Geri bildiriminiz kaydedildi');
    } catch (error) {
      console.error('Error submitting feedback:', error);
      toast.error('Geri bildirim gönderilemedi');
    }
  };

  return (
    <DashboardLayout title="AI Asistan">
      <div className="flex h-[calc(100vh-12rem)] gap-4">
        {/* Conversation List */}
        <Card className="w-80 flex-shrink-0">
          <div className="p-4 border-b">
            <Button
              onClick={handleCreateConversation}
              disabled={isCreating}
              className="w-full"
            >
              {isCreating ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Plus className="mr-2 h-4 w-4" />
              )}
              Yeni Sohbet
            </Button>
          </div>
          <ScrollArea className="h-[calc(100%-5rem)]">
            {isLoadingConversations ? (
              <div className="p-4 space-y-3">
                {[...Array(5)].map((_, i) => (
                  <Skeleton key={i} className="h-16 w-full" />
                ))}
              </div>
            ) : conversations.length === 0 ? (
              <div className="p-8 text-center text-slate-500">
                <MessageSquare className="mx-auto h-12 w-12 text-slate-300 mb-4" />
                <p>Henüz sohbet yok</p>
                <p className="text-sm mt-2">Yeni bir sohbet başlatın</p>
              </div>
            ) : (
              <div className="p-2">
                {conversations.map((conv) => (
                  <div
                    key={conv.id}
                    onClick={() => setActiveConversation(conv)}
                    className={cn(
                      'p-3 rounded-lg cursor-pointer transition-colors group',
                      activeConversation?.id === conv.id
                        ? 'bg-primary/10 border border-primary/20'
                        : 'hover:bg-slate-100'
                    )}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <p className="font-medium truncate">
                          {conv.title || 'Yeni Sohbet'}
                        </p>
                        <p className="text-xs text-slate-500 mt-1">
                          {conv.message_count} mesaj
                        </p>
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="opacity-0 group-hover:opacity-100 h-8 w-8"
                        onClick={(e) => handleDeleteConversation(conv.id, e)}
                      >
                        <Trash2 className="h-4 w-4 text-red-500" />
                      </Button>
                    </div>
                    <p className="text-xs text-slate-400 mt-2">
                      {formatDistanceToNow(new Date(conv.updated_at), {
                        addSuffix: true,
                        locale: tr,
                      })}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </ScrollArea>
        </Card>

        {/* Chat Window */}
        <Card className="flex-1 flex flex-col">
          {!activeConversation ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <Bot className="mx-auto h-16 w-16 text-slate-300 mb-4" />
                <h3 className="text-xl font-medium text-slate-900 mb-2">
                  İşNet AI Asistan
                </h3>
                <p className="text-slate-500 max-w-md">
                  Dokümanlarınız hakkında sorular sorun, AI asistan size yardımcı olsun.
                  Başlamak için yeni bir sohbet oluşturun veya mevcut bir sohbeti seçin.
                </p>
              </div>
            </div>
          ) : (
            <>
              {/* Messages */}
              <ScrollArea className="flex-1 p-4">
                {isLoadingMessages ? (
                  <div className="space-y-4">
                    {[...Array(3)].map((_, i) => (
                      <Skeleton key={i} className="h-24 w-3/4" />
                    ))}
                  </div>
                ) : messages.length === 0 ? (
                  <div className="h-full flex items-center justify-center">
                    <div className="text-center text-slate-500">
                      <MessageSquare className="mx-auto h-12 w-12 text-slate-300 mb-4" />
                      <p>Henüz mesaj yok</p>
                      <p className="text-sm mt-2">Bir soru sorarak başlayın</p>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {messages.map((message) => (
                      <div
                        key={message.id}
                        className={cn(
                          'flex gap-3',
                          message.role === 'user' ? 'justify-end' : 'justify-start'
                        )}
                      >
                        {message.role !== 'user' && (
                          <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                            <Bot className="h-5 w-5 text-primary" />
                          </div>
                        )}
                        <div
                          className={cn(
                            'max-w-[70%] rounded-lg p-4',
                            message.role === 'user'
                              ? 'bg-primary text-primary-foreground'
                              : 'bg-slate-100'
                          )}
                        >
                          <p className="whitespace-pre-wrap">{message.content}</p>

                          {/* Sources */}
                          {message.sources && message.sources.length > 0 && (
                            <div className="mt-3 pt-3 border-t border-slate-200">
                              <p className="text-xs font-medium mb-2 flex items-center gap-1">
                                <FileText className="h-3 w-3" />
                                Kaynaklar
                              </p>
                              <div className="space-y-2">
                                {message.sources.map((source, idx) => (
                                  <div
                                    key={idx}
                                    className="text-xs bg-white rounded p-2 border"
                                  >
                                    {source.document_title && (
                                      <p className="font-medium text-primary">
                                        {source.document_title}
                                      </p>
                                    )}
                                    <p className="text-slate-600 line-clamp-2 mt-1">
                                      {source.content}
                                    </p>
                                    {source.relevance && (
                                      <p className="text-slate-400 mt-1">
                                        İlgililik: %{Math.round(source.relevance * 100)}
                                      </p>
                                    )}
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Response time */}
                          {message.response_time_ms && (
                            <p className="text-xs text-slate-400 mt-2 flex items-center gap-1">
                              <Clock className="h-3 w-3" />
                              {(message.response_time_ms / 1000).toFixed(2)}s
                            </p>
                          )}

                          {/* Feedback */}
                          {message.role === 'assistant' && message.id !== 'temp-user' && (
                            <div className="mt-3 pt-3 border-t border-slate-200 flex items-center gap-2">
                              <span className="text-xs text-slate-500">Faydalı mıydı?</span>
                              <Button
                                variant="ghost"
                                size="icon"
                                className={cn(
                                  'h-7 w-7',
                                  message.is_helpful === true && 'text-green-600 bg-green-50'
                                )}
                                onClick={() => handleFeedback(message.id, true)}
                              >
                                <ThumbsUp className="h-4 w-4" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="icon"
                                className={cn(
                                  'h-7 w-7',
                                  message.is_helpful === false && 'text-red-600 bg-red-50'
                                )}
                                onClick={() => handleFeedback(message.id, false)}
                              >
                                <ThumbsDown className="h-4 w-4" />
                              </Button>
                            </div>
                          )}
                        </div>
                        {message.role === 'user' && (
                          <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center flex-shrink-0">
                            <User className="h-5 w-5 text-slate-600" />
                          </div>
                        )}
                      </div>
                    ))}

                    {/* Typing indicator */}
                    {isSending && (
                      <div className="flex gap-3">
                        <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                          <Bot className="h-5 w-5 text-primary" />
                        </div>
                        <div className="bg-slate-100 rounded-lg p-4">
                          <div className="flex gap-1">
                            <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" />
                            <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce delay-100" />
                            <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce delay-200" />
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </ScrollArea>

              {/* Input */}
              <div className="p-4 border-t">
                <form onSubmit={handleSendMessage} className="flex gap-2">
                  <Input
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    placeholder="Sorunuzu yazın..."
                    disabled={isSending}
                    className="flex-1"
                  />
                  <Button type="submit" disabled={!inputMessage.trim() || isSending}>
                    {isSending ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Send className="h-4 w-4" />
                    )}
                  </Button>
                </form>
              </div>
            </>
          )}
        </Card>
      </div>
    </DashboardLayout>
  );
}
