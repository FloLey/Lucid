import { useCallback, useEffect, useRef } from 'react';
import * as api from '../services/api';
import { getErrorMessage } from '../utils/error';
import type { Project } from '../types';

interface UseDebouncedRenderOptions {
  projectId: string;
  slideIndex: number;
  onSuccess: (project: Project) => void;
  onError: (error: string) => void;
}

/**
 * Debounces text edits so that a sync (save) followed by a render request
 * fires once per burst of keystrokes rather than on every keystroke.
 *
 * Render always follows a successful sync, eliminating the race condition
 * that existed when the two timers were managed separately in Stage5.
 */
export function useDebouncedRender({
  projectId,
  slideIndex,
  onSuccess,
  onError,
}: UseDebouncedRenderOptions) {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const latestTitleRef = useRef<string | null>(null);
  const latestBodyRef = useRef<string>('');

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  const _doSyncAndRender = useCallback(
    async (title: string | null, body: string) => {
      try {
        const synced = await api.updateSlideText(
          projectId,
          slideIndex,
          title ?? undefined,
          body,
        );
        onSuccess(synced);
        const rendered = await api.applyTextToSlide(projectId, slideIndex);
        onSuccess(rendered);
      } catch (err) {
        onError(getErrorMessage(err, 'Failed to save text'));
      }
    },
    [projectId, slideIndex, onSuccess, onError],
  );

  /** Schedule a debounced sync + render after 1 s of inactivity. */
  const schedule = useCallback(
    (title: string | null, body: string) => {
      latestTitleRef.current = title;
      latestBodyRef.current = body;

      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => {
        timerRef.current = null;
        _doSyncAndRender(latestTitleRef.current, latestBodyRef.current);
      }, 1000);
    },
    [_doSyncAndRender],
  );

  /**
   * Immediately cancel any pending timer and execute sync + render now.
   * No-op if no timer is pending (i.e. text is already in sync).
   */
  const flush = useCallback(async () => {
    if (!timerRef.current) return;
    clearTimeout(timerRef.current);
    timerRef.current = null;
    await _doSyncAndRender(latestTitleRef.current, latestBodyRef.current);
  }, [_doSyncAndRender]);

  return { schedule, flush };
}
