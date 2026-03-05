import { useState, useCallback, useRef, useEffect } from 'react';
import type { MatrixProject, MatrixCell, MatrixSSEEvent } from '../types';
import { getMatrixStreamUrl } from '../services/api';
import { getErrorMessage } from '../utils/error';

const SSE_DATA_PREFIX = 'data: ';

interface UseMatrixStreamOptions {
  onUpdate: (updater: (prev: MatrixProject) => MatrixProject) => void;
  onComplete: () => void;
  onError: (message: string) => void;
}

function patchCell(
  project: MatrixProject,
  row: number,
  col: number,
  patch: Partial<MatrixCell>,
): MatrixProject {
  return {
    ...project,
    cells: project.cells.map((cell) =>
      cell.row === row && cell.col === col ? { ...cell, ...patch } : cell
    ),
  };
}

export function useMatrixStream({
  onUpdate,
  onComplete,
  onError,
}: UseMatrixStreamOptions) {
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  // Keep callback refs current so startStream always calls the latest versions
  // without needing them in its dependency array.
  const onUpdateRef = useRef(onUpdate);
  const onCompleteRef = useRef(onComplete);
  const onErrorRef = useRef(onError);
  onUpdateRef.current = onUpdate;
  onCompleteRef.current = onComplete;
  onErrorRef.current = onError;

  useEffect(
    () => () => {
      abortRef.current?.abort();
    },
    [],
  );

  const startStream = useCallback(
    async (projectId: string) => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      setIsStreaming(true);

      try {
        const response = await fetch(getMatrixStreamUrl(projectId), {
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

          // SSE lines are delimited by \n\n
          const chunks = buffer.split('\n\n');
          buffer = chunks.pop() ?? '';

          for (const chunk of chunks) {
            const line = chunk.trim();
            if (!line.startsWith(SSE_DATA_PREFIX)) continue;
            try {
              const event = JSON.parse(line.slice(SSE_DATA_PREFIX.length)) as MatrixSSEEvent;
              handleEvent(event);
              if (event.type === 'done') {
                setIsStreaming(false);
                onCompleteRef.current();
                return;
              }
              if (event.type === 'error') {
                setIsStreaming(false);
                onErrorRef.current(event.message);
                return;
              }
            } catch (e) {
              console.warn('Failed to parse SSE message:', line, e);
            }
          }
        }
      } catch (err) {
        if (err instanceof Error && err.name === 'AbortError') return;
        onErrorRef.current(getErrorMessage(err, 'Stream connection failed'));
      } finally {
        setIsStreaming(false);
      }
    },
    [],
  );

  function handleEvent(event: MatrixSSEEvent) {
    switch (event.type) {
      case 'snapshot':
        onUpdateRef.current(() => event.matrix);
        break;

      case 'diagonal':
        onUpdateRef.current((prev) =>
          patchCell(prev, event.index, event.index, {
            label: event.label,
            definition: event.definition,
            cell_status: 'complete',
          })
        );
        break;

      case 'axes':
        onUpdateRef.current((prev) =>
          patchCell(prev, event.row, event.col, {
            row_descriptor: event.row_descriptor,
            col_descriptor: event.col_descriptor,
          })
        );
        break;

      case 'cell': {
        // For diagonal cells in description mode the server emits a "cell" event
        // (not "diagonal"). Mirror concept→label / explanation→definition so the
        // reveal-view display logic, which reads `cell.label` for diagonal cells,
        // still works correctly during live streaming.
        const isDiag = event.row === event.col;
        onUpdateRef.current((prev) =>
          patchCell(prev, event.row, event.col, {
            concept: event.concept,
            explanation: event.explanation,
            cell_status: 'complete',
            ...(isDiag ? { label: event.concept, definition: event.explanation } : {}),
          })
        );
        break;
      }

      case 'cell_failed':
        onUpdateRef.current((prev) =>
          patchCell(prev, event.row, event.col, {
            cell_status: 'failed',
            cell_error: event.error,
          })
        );
        break;

      case 'image':
        onUpdateRef.current((prev) =>
          patchCell(prev, event.row, event.col, {
            image_url: event.image_url,
          })
        );
        break;

      case 'validation':
        // Mark cells being retried as 'generating'
        onUpdateRef.current((prev) => {
          let updated = prev;
          for (const { row, col } of event.failures) {
            updated = patchCell(updated, row, col, { cell_status: 'generating' });
          }
          return updated;
        });
        break;

      case 'heartbeat':
      case 'progress':
        // No UI update needed
        break;
    }
  }

  const stopStream = useCallback(() => {
    abortRef.current?.abort();
    setIsStreaming(false);
  }, []);

  return { isStreaming, startStream, stopStream };
}
