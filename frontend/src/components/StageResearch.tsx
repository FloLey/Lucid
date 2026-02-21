import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import * as api from '../services/api';
import { getErrorMessage } from '../utils/error';
import { useProject } from '../contexts/ProjectContext';
import Spinner from './Spinner';
import type { ChatMessage } from '../types';

export default function StageResearch() {
  const {
    projectId,
    currentProject: project,
    setError,
    updateProject,
  } = useProject();

  const [message, setMessage] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [extractLoading, setExtractLoading] = useState(false);
  const [researchInstructions, setResearchInstructions] = useState(
    project?.research_instructions ?? ''
  );

  const chatEndRef = useRef<HTMLDivElement>(null);

  // Sync instructions if project changes (e.g., on open)
  useEffect(() => {
    if (project?.research_instructions !== undefined) {
      setResearchInstructions(project.research_instructions ?? '');
    }
  }, [project?.research_instructions]);

  // Auto-scroll to the bottom whenever chat history grows
  useEffect(() => {
    chatEndRef.current?.scrollIntoView?.({ behavior: 'smooth' });
  }, [project?.chat_history]);

  const chatHistory: ChatMessage[] = project?.chat_history ?? [];

  const handleSend = async () => {
    const trimmed = message.trim();
    if (!trimmed || chatLoading) return;

    setMessage('');
    setChatLoading(true);
    setError(null);
    try {
      const updated = await api.sendResearchMessage(projectId, trimmed);
      updateProject(updated);
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to send message'));
    } finally {
      setChatLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleExtractDraft = async () => {
    if (extractLoading) return;
    setExtractLoading(true);
    setError(null);
    try {
      const updated = await api.extractDraftFromResearch(
        projectId,
        researchInstructions.trim() || undefined
      );
      updateProject(updated);
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to extract draft'));
    } finally {
      setExtractLoading(false);
    }
  };

  return (
    <div className="flex flex-col lg:flex-row gap-6 h-full" style={{ minHeight: '70vh' }}>
      {/* ── Left column: Chat UI ───────────────────────────────────────── */}
      <div className="flex flex-col flex-1 min-w-0 bg-white dark:bg-gray-800 rounded-xl shadow border border-gray-200 dark:border-gray-700 overflow-hidden">
        {/* Header */}
        <div className="px-5 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Research Chat
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
            Chat with AI, grounded by Google Search. Ask questions, explore ideas, gather facts.
          </p>
        </div>

        {/* Message list */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
          {chatHistory.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-center text-gray-400 dark:text-gray-500 py-12">
              <svg className="w-12 h-12 mb-4 opacity-40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
              <p className="text-sm">Start the conversation below.</p>
              <p className="text-xs mt-1 opacity-70">
                AI responses are grounded by Google Search.
              </p>
            </div>
          )}

          {chatHistory.map((turn, idx) => (
            <div
              key={idx}
              className={`flex ${turn.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                  turn.role === 'user'
                    ? 'bg-lucid-600 text-white rounded-br-sm'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-100 rounded-bl-sm'
                }`}
              >
                {turn.role === 'model' ? (
                  <div className="prose prose-sm dark:prose-invert max-w-none">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {turn.content}
                    </ReactMarkdown>
                  </div>
                ) : (
                  <span>{turn.content}</span>
                )}
              </div>
            </div>
          ))}

          {chatLoading && (
            <div className="flex justify-start">
              <div className="bg-gray-100 dark:bg-gray-700 rounded-2xl rounded-bl-sm px-4 py-3">
                <Spinner />
              </div>
            </div>
          )}

          <div ref={chatEndRef} />
        </div>

        {/* Input */}
        <div className="px-4 py-3 border-t border-gray-200 dark:border-gray-700 flex gap-2 items-end">
          <textarea
            className="flex-1 resize-none rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-lucid-500 min-h-[42px] max-h-32"
            placeholder="Ask a question… (Enter to send, Shift+Enter for newline)"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
            disabled={chatLoading}
          />
          <button
            onClick={handleSend}
            disabled={chatLoading || !message.trim()}
            className="shrink-0 px-4 py-2 rounded-lg bg-lucid-600 text-white text-sm font-medium hover:bg-lucid-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Send
          </button>
        </div>
      </div>

      {/* ── Right column: Extraction panel ────────────────────────────── */}
      <div className="w-full lg:w-80 flex flex-col gap-4 shrink-0">
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow border border-gray-200 dark:border-gray-700 p-5">
          <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-1">
            Create Draft
          </h3>
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">
            Summarise the conversation into a draft, then continue to the Draft stage.
          </p>

          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Formatting instructions (optional)
          </label>
          <textarea
            className="w-full resize-none rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-lucid-500 min-h-[90px]"
            placeholder={'e.g. "Summarise into 3 key arguments" or "Focus on statistics"'}
            value={researchInstructions}
            onChange={(e) => setResearchInstructions(e.target.value)}
          />

          <button
            onClick={handleExtractDraft}
            disabled={extractLoading || chatHistory.length === 0}
            className="mt-4 w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-lucid-600 text-white text-sm font-semibold hover:bg-lucid-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {extractLoading ? (
              <>
                <Spinner />
                <span>Creating draft…</span>
              </>
            ) : (
              'Create Draft & Proceed →'
            )}
          </button>

          {chatHistory.length === 0 && (
            <p className="mt-2 text-xs text-center text-gray-400 dark:text-gray-500">
              Start a conversation first.
            </p>
          )}
        </div>

        {/* Skip option */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow border border-gray-200 dark:border-gray-700 p-5">
          <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Skip Research
          </h3>
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
            Already have your content ready? Go straight to the Draft stage.
          </p>
          <button
            onClick={async () => {
              try {
                const updated = await api.goToStage(projectId, 2);
                updateProject(updated);
              } catch (err) {
                setError(getErrorMessage(err, 'Navigation failed'));
              }
            }}
            className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 text-sm hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          >
            Go to Draft →
          </button>
        </div>
      </div>
    </div>
  );
}
