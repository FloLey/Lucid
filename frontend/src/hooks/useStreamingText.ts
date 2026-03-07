import { useState, useCallback, useRef, useEffect } from 'react';
import * as api from '../services/api';
import { getErrorMessage } from '../utils/error';
import { parseSSELine } from '../utils/sse';
import type { Project } from '../types';

interface UseStreamingTextOptions {
  projectId: string;
  onProjectUpdate: (project: Project) => void;
  onError: (message: string) => void;
}

interface UseStreamingTextResult {
  streamingTexts: Map<number, string>;
  startStream: (slideIndex: number, instruction?: string) => Promise<void>;
  isStreaming: (slideIndex: number) => boolean;
}

export function useStreamingText({
  projectId,
  onProjectUpdate,
  onError,
}: UseStreamingTextOptions): UseStreamingTextResult {
  const [streamingTexts, setStreamingTexts] = useState<Map<number, string>>(new Map());
  const abortRef = useRef<AbortController | null>(null);

  // Abort any in-flight stream when the component unmounts
  useEffect(() => () => { abortRef.current?.abort(); }, []);

  const startStream = useCallback(
    async (index: number, instruction?: string) => {
      // Cancel any previous stream before starting a new one
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      setStreamingTexts((prev) => new Map(prev).set(index, ''));

      try {
        const response = await fetch('/api/stage-draft/regenerate-stream', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            project_id: projectId,
            slide_index: index,
            instruction: instruction || null,
          }),
          signal: controller.signal,
        });

        if (!response.ok || !response.body) {
          throw new Error(`HTTP ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        for (;;) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });

          const lines = buffer.split('\n');
          buffer = lines.pop() ?? '';

          for (const line of lines) {
            const data = parseSSELine<{ text?: string; done?: boolean }>(line);
            if (data === null) continue;
            if (typeof data.text === 'string') {
              setStreamingTexts((prev) => new Map(prev).set(index, data.text!));
            }
            if (data.done) {
              const refreshed = await api.getProject(projectId);
              onProjectUpdate(refreshed);
              setStreamingTexts((prev) => {
                const next = new Map(prev);
                next.delete(index);
                return next;
              });
            }
          }
        }
      } catch (err) {
        if (err instanceof Error && err.name === 'AbortError') return;
        onError(getErrorMessage(err, `Failed to regenerate slide ${index + 1}`));
        setStreamingTexts((prev) => {
          const next = new Map(prev);
          next.delete(index);
          return next;
        });
      }
    },
    [projectId, onProjectUpdate, onError],
  );

  const isStreaming = useCallback(
    (index: number) => streamingTexts.has(index),
    [streamingTexts],
  );

  return { streamingTexts, startStream, isStreaming };
}
