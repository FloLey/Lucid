import { useState, useRef, useEffect } from 'react';
import type { Session } from '../types';
import { sendChatMessage } from '../services/api';

interface ChatBarProps {
  sessionId: string;
  isOpen: boolean;
  onToggle: () => void;
  updateSession: (session: Session) => void;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  toolCalled?: string;
}

export default function ChatBar({ sessionId, isOpen, onToggle, updateSession }: ChatBarProps) {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await sendChatMessage(sessionId, input);

      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.response,
        toolCalled: response.tool_called || undefined,
      };

      setMessages((prev) => [...prev, assistantMessage]);

      if (response.session) {
        updateSession(response.session);
      }
    } catch (err) {
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'Sorry, something went wrong. Please try again.',
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50">
      {isOpen && (
        <div className="bg-white border-t border-gray-200 shadow-lg max-h-80 overflow-y-auto">
          <div className="container mx-auto px-4 py-3">
            <div className="space-y-3">
              {messages.length === 0 ? (
                <div className="text-center text-gray-400 text-sm py-4">
                  Type a message or use commands like <code className="bg-gray-100 px-1 rounded">/next</code> or <code className="bg-gray-100 px-1 rounded">/regen slide 2</code>
                </div>
              ) : (
                messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-md px-4 py-2 rounded-lg ${
                        msg.role === 'user'
                          ? 'bg-lucid-600 text-white'
                          : 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      <p>{msg.content}</p>
                      {msg.toolCalled && (
                        <p className="text-xs mt-1 opacity-70">
                          Tool: {msg.toolCalled}
                        </p>
                      )}
                    </div>
                  </div>
                ))
              )}
              <div ref={messagesEndRef} />
            </div>
          </div>
        </div>
      )}

      <div className="bg-white border-t border-gray-200">
        <div className="container mx-auto px-4 py-3">
          <form onSubmit={handleSubmit} className="flex items-center gap-3">
            <button
              type="button"
              onClick={onToggle}
              className="p-2 text-gray-500 hover:text-gray-700"
            >
              {isOpen ? '▼' : '▲'}
            </button>

            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type a command or ask for help..."
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-lucid-500 focus:border-transparent"
              disabled={loading}
            />

            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="px-4 py-2 bg-lucid-600 text-white rounded-lg hover:bg-lucid-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? '...' : 'Send'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
