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
  const [proceedLoading, setProceedLoading] = useState(false);
  const [researchInstructions, setResearchInstructions] = useState(
    project?.research_instructions ?? ''
  );
  // Optimistic user message shown while waiting for the AI reply
  const [pendingUserMessage, setPendingUserMessage] = useState<string | null>(null);

  const chatEndRef = useRef<HTMLDivElement>(null);

  // Sync instructions if project changes (e.g., on open)
  useEffect(() => {
    if (project?.research_instructions !== undefined) {
      setResearchInstructions(project.research_instructions ?? '');
    }
  }, [project?.research_instructions]);

  // Auto-scroll to the bottom whenever chat history grows or a pending message is added
  useEffect(() => {
    chatEndRef.current?.scrollIntoView?.({ behavior: 'smooth' });
  }, [project?.chat_history, pendingUserMessage, chatLoading]);

  const chatHistory: ChatMessage[] = project?.chat_history ?? [];
  const hasDraft = Boolean(project?.draft_text?.trim());

  const handleSend = async () => {
    const trimmed = message.trim();
    if (!trimmed || chatLoading) return;

    setMessage('');
    setPendingUserMessage(trimmed);
    setChatLoading(true);
    setError(null);
    try {
      const updated = await api.sendResearchMessage(projectId, trimmed);
      updateProject(updated);
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to send message'));
      // Restore message so user can retry
      setMessage(trimmed);
    } finally {
      setPendingUserMessage(null);
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

  const handleProceedToStage2 = async () => {
    if (proceedLoading) return;
    setProceedLoading(true);
    setError(null);
    try {
      const updated = await api.goToStage(projectId, 2);
      updateProject(updated);
    } catch (err) {
      setError(getErrorMessage(err, 'Navigation failed'));
    } finally {
      setProceedLoading(false);
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
          {chatHistory.length === 0 && !pendingUserMessage && (
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
                  <>
                    <div className="prose prose-sm dark:prose-invert max-w-none">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {turn.content}
                      </ReactMarkdown>
                    </div>
                    {turn.grounded && (
                      <div className="mt-2 flex items-center gap-1 text-xs text-gray-400 dark:text-gray-500">
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                            d="M21 21l-4.35-4.35M17 11A6 6 0 115 11a6 6 0 0112 0z" />
                        </svg>
                        <span>Grounded with Google Search</span>
                      </div>
                    )}
                  </>
                ) : (
                  <span>{turn.content}</span>
                )}
              </div>
            </div>
          ))}

          {/* Optimistic user message shown immediately while waiting for reply */}
          {pendingUserMessage && (
            <div className="flex justify-end">
              <div className="max-w-[85%] rounded-2xl rounded-br-sm px-4 py-3 text-sm leading-relaxed bg-lucid-600 text-white opacity-80">
                <span>{pendingUserMessage}</span>
              </div>
            </div>
          )}

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
        {/* Create Draft section */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow border border-gray-200 dark:border-gray-700 p-5">
          <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-1">
            Create Draft
          </h3>
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">
            Summarise the conversation into a draft text.
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
              hasDraft ? 'Regenerate Draft' : 'Create Draft'
            )}
          </button>

          {chatHistory.length === 0 && (
            <p className="mt-2 text-xs text-center text-gray-400 dark:text-gray-500">
              Start a conversation first.
            </p>
          )}
        </div>

        {/* Draft preview + proceed section */}
        {hasDraft && (
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow border border-lucid-200 dark:border-lucid-700 p-5">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2 flex items-center gap-2">
              <svg className="w-4 h-4 text-lucid-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Draft Ready
            </h3>
            <div className="max-h-48 overflow-y-auto rounded-lg bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 px-3 py-2 text-xs text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-wrap">
              {project?.draft_text}
            </div>
            <button
              onClick={handleProceedToStage2}
              disabled={proceedLoading}
              className="mt-3 w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-green-600 text-white text-sm font-semibold hover:bg-green-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              {proceedLoading ? (
                <>
                  <Spinner />
                  <span>Proceeding…</span>
                </>
              ) : (
                'Proceed to Draft Stage →'
              )}
            </button>
          </div>
        )}

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
