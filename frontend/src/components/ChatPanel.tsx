import { useState, useRef, useEffect, useCallback } from 'react';
import type { Session, ChatMessage, ChatEvent } from '../types';
import { sendChatMessageSSE, cancelAgent, undoAgent } from '../services/api';

interface ChatPanelProps {
  sessionId: string;
  currentStage: number;
  updateSession: (session: Session) => void;
}

// Stage-specific commands for autocomplete
const STAGE_COMMANDS: Record<number, { command: string; description: string }[]> = {
  1: [
    { command: '/next', description: 'Advance to Stage 2' },
    { command: '/generate', description: 'Generate slides from draft' },
    { command: '/regen slide', description: 'Regenerate a specific slide' },
  ],
  2: [
    { command: '/back', description: 'Go back to Stage 1' },
    { command: '/next', description: 'Advance to Stage 3' },
    { command: '/generate', description: 'Generate style proposals' },
  ],
  3: [
    { command: '/back', description: 'Go back to Stage 2' },
    { command: '/next', description: 'Advance to Stage 4' },
    { command: '/generate', description: 'Generate image prompts' },
    { command: '/regen prompt', description: 'Regenerate a specific prompt' },
  ],
  4: [
    { command: '/back', description: 'Go back to Stage 3' },
    { command: '/next', description: 'Advance to Stage 5' },
    { command: '/generate', description: 'Generate background images' },
    { command: '/regen image', description: 'Regenerate a specific image' },
  ],
  5: [
    { command: '/back', description: 'Go back to Stage 4' },
    { command: '/generate', description: 'Apply typography' },
    { command: '/export', description: 'Export carousel as ZIP' },
  ],
};

export default function ChatPanel({ sessionId, currentStage, updateSession }: ChatPanelProps) {
  const nextIdRef = useRef(1);
  const genId = useCallback(() => String(nextIdRef.current++), []);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [processing, setProcessing] = useState(false);
  const [canUndo, setCanUndo] = useState(false);
  const [showAutocomplete, setShowAutocomplete] = useState(false);
  const [filteredCommands, setFilteredCommands] = useState<{ command: string; description: string }[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Handle autocomplete
  useEffect(() => {
    if (input.startsWith('/')) {
      const commands = STAGE_COMMANDS[currentStage] || [];
      const query = input.toLowerCase();
      const filtered = commands.filter((c) =>
        c.command.toLowerCase().startsWith(query)
      );
      setFilteredCommands(filtered);
      setShowAutocomplete(filtered.length > 0);
    } else {
      setShowAutocomplete(false);
    }
  }, [input, currentStage]);

  const handleCommandSelect = (command: string) => {
    setInput(command + ' ');
    setShowAutocomplete(false);
    inputRef.current?.focus();
  };

  const handleEvent = useCallback((evt: ChatEvent) => {
    switch (evt.event) {
      case 'thinking':
        setMessages((prev) => [...prev, {
          id: genId(), type: 'thinking', content: evt.text,
        }]);
        break;
      case 'text':
        setMessages((prev) => [...prev, {
          id: genId(), type: 'text', content: evt.text,
        }]);
        break;
      case 'tool_call':
        setMessages((prev) => [...prev, {
          id: genId(), type: 'tool_call', content: `Calling ${evt.name}`,
          toolName: evt.name, toolArgs: evt.args,
        }]);
        break;
      case 'tool_result':
        setMessages((prev) => [...prev, {
          id: genId(), type: 'tool_result',
          content: evt.result.message as string || evt.result.error as string || JSON.stringify(evt.result),
          toolName: evt.name, toolResult: evt.result,
        }]);
        break;
      case 'error':
        setMessages((prev) => [...prev, {
          id: genId(), type: 'error', content: evt.message,
        }]);
        break;
      case 'done':
        if (evt.session) {
          updateSession(evt.session);
        }
        setCanUndo(evt.has_writes);
        setProcessing(false);
        break;
    }
  }, [updateSession]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const msg = input.trim();
    if (!msg || processing) return;

    setShowAutocomplete(false);
    setMessages((prev) => [...prev, { id: genId(), type: 'user', content: msg }]);
    setInput('');
    setProcessing(true);
    setCanUndo(false);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      await sendChatMessageSSE(sessionId, msg, handleEvent, controller.signal);
    } catch {
      if (!controller.signal.aborted) {
        setMessages((prev) => [...prev, {
          id: genId(), type: 'error', content: 'Connection failed. Please try again.',
        }]);
      }
      setProcessing(false);
    }
  };

  const handleStop = async () => {
    abortRef.current?.abort();
    try {
      await cancelAgent(sessionId);
    } catch {
      // ignore
    }
    setProcessing(false);
  };

  const handleUndo = async () => {
    try {
      const session = await undoAgent(sessionId);
      updateSession(session);
      setMessages((prev) => [...prev, {
        id: genId(), type: 'text', content: 'Undone. Session restored to previous state.',
      }]);
      setCanUndo(false);
    } catch {
      setMessages((prev) => [...prev, {
        id: genId(), type: 'error', content: 'Nothing to undo.',
      }]);
    }
  };

  return (
    <div className="w-96 border-l border-gray-200 bg-white flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
        <h2 className="font-semibold text-gray-800">Chat</h2>
        <div className="flex items-center gap-2">
          {canUndo && (
            <button
              onClick={handleUndo}
              className="text-xs px-2 py-1 text-amber-700 bg-amber-50 border border-amber-200 rounded hover:bg-amber-100 transition-colors"
              title="Undo last agent changes"
            >
              Undo
            </button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
        {messages.length === 0 ? (
          <div className="text-center text-gray-400 text-sm py-8">
            Ask me to modify your carousel, or use commands like{' '}
            <code className="bg-gray-100 px-1 rounded">/next</code>
          </div>
        ) : (
          messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 px-4 py-3 relative">
        {/* Autocomplete */}
        {showAutocomplete && (
          <div className="absolute bottom-full left-0 right-0 bg-white border border-gray-200 rounded-t-lg shadow-lg max-h-48 overflow-y-auto">
            {filteredCommands.map((cmd) => (
              <button
                key={cmd.command}
                type="button"
                onClick={() => handleCommandSelect(cmd.command)}
                className="w-full flex items-center justify-between px-3 py-2 hover:bg-gray-50 text-left border-b border-gray-100 last:border-0"
              >
                <code className="text-lucid-600 font-mono text-sm">{cmd.command}</code>
                <span className="text-gray-500 text-xs">{cmd.description}</span>
              </button>
            ))}
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex items-center gap-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type / for commands..."
            className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-lucid-500 focus:border-transparent"
          />
          {processing ? (
            <button
              type="button"
              onClick={handleStop}
              className="px-3 py-2 text-sm bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors"
            >
              Stop
            </button>
          ) : (
            <button
              type="submit"
              disabled={!input.trim()}
              className="px-3 py-2 text-sm bg-lucid-600 text-white rounded-lg hover:bg-lucid-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Send
            </button>
          )}
        </form>
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const [expanded, setExpanded] = useState(false);

  if (message.type === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-xs px-3 py-2 bg-lucid-600 text-white rounded-lg text-sm">
          {message.content}
        </div>
      </div>
    );
  }

  if (message.type === 'thinking') {
    return (
      <div className="flex justify-start">
        <div className="max-w-xs px-3 py-2 bg-purple-50 text-purple-700 border border-purple-200 rounded-lg text-xs italic">
          <span className="font-medium">Thinking:</span> {message.content}
        </div>
      </div>
    );
  }

  if (message.type === 'tool_call') {
    return (
      <div className="flex justify-start">
        <button
          onClick={() => setExpanded(!expanded)}
          className="max-w-xs px-3 py-2 bg-blue-50 text-blue-700 border border-blue-200 rounded-lg text-xs cursor-pointer hover:bg-blue-100 transition-colors text-left"
        >
          <span className="font-medium">Tool:</span> {message.toolName}
          {message.toolArgs && Object.keys(message.toolArgs).length > 0 && (
            <span className="text-blue-500"> ({Object.entries(message.toolArgs).map(([k, v]) => `${k}=${JSON.stringify(v)}`).join(', ')})</span>
          )}
          {expanded && (
            <pre className="mt-1 text-xs overflow-x-auto">{JSON.stringify(message.toolArgs, null, 2)}</pre>
          )}
        </button>
      </div>
    );
  }

  if (message.type === 'tool_result') {
    const isSuccess = message.toolResult?.success !== false;
    return (
      <div className="flex justify-start">
        <button
          onClick={() => setExpanded(!expanded)}
          className={`max-w-xs px-3 py-2 rounded-lg text-xs cursor-pointer transition-colors text-left ${
            isSuccess
              ? 'bg-green-50 text-green-700 border border-green-200 hover:bg-green-100'
              : 'bg-red-50 text-red-700 border border-red-200 hover:bg-red-100'
          }`}
        >
          <span className="font-medium">{isSuccess ? 'OK' : 'Error'}:</span> {message.content}
          {expanded && (
            <pre className="mt-1 text-xs overflow-x-auto">{JSON.stringify(message.toolResult, null, 2)}</pre>
          )}
        </button>
      </div>
    );
  }

  if (message.type === 'error') {
    return (
      <div className="flex justify-start">
        <div className="max-w-xs px-3 py-2 bg-red-50 text-red-700 border border-red-200 rounded-lg text-sm">
          {message.content}
        </div>
      </div>
    );
  }

  // text type
  return (
    <div className="flex justify-start">
      <div className="max-w-xs px-3 py-2 bg-gray-100 text-gray-800 rounded-lg text-sm">
        {message.content}
      </div>
    </div>
  );
}
