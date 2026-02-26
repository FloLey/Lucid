import { useState, useCallback, useEffect, useRef } from 'react';
import type { TextStyle } from '../types';
import * as api from '../services/api';

interface UseStyleManagerOptions {
  projectId: string;
  slideIndex: number;
  initialStyle: TextStyle | null;
}

export function useStyleManager({
  projectId,
  slideIndex,
  initialStyle,
}: UseStyleManagerOptions) {
  const [style, setStyle] = useState<TextStyle | null>(initialStyle);
  const [isUpdating, setIsUpdating] = useState(false);

  // styleRef so callbacks always read the latest value without stale closures
  const styleRef = useRef(style);
  styleRef.current = style;

  // Undo/redo history stacks (refs to avoid triggering re-renders)
  const historyRef = useRef<TextStyle[]>([]);
  const futureRef = useRef<TextStyle[]>([]);

  const _commitStyle = useCallback(
    async (newStyle: TextStyle, fallback: TextStyle | null) => {
      setStyle(newStyle);
      setIsUpdating(true);
      try {
        await api.updateStyle(projectId, slideIndex, newStyle);
      } catch (error) {
        setStyle(fallback);
        throw error;
      } finally {
        setIsUpdating(false);
      }
    },
    [projectId, slideIndex],
  );

  const updateStyle = useCallback(
    async (updates: Partial<TextStyle>) => {
      const current = styleRef.current;
      if (!current) return;

      const newStyle = structuredClone(current);
      for (const [key, value] of Object.entries(updates)) {
        if (key === 'title_box' || key === 'body_box') {
          Object.assign((newStyle as unknown as Record<string, unknown>)[key] as object, value);
        } else if (key === 'stroke' || key === 'shadow') {
          const existing = (newStyle as unknown as Record<string, unknown>)[key];
          if (existing) {
            Object.assign(existing as object, value);
          } else {
            (newStyle as unknown as Record<string, unknown>)[key] = value;
          }
        } else {
          (newStyle as unknown as Record<string, unknown>)[key] = value;
        }
      }

      historyRef.current = [...historyRef.current.slice(-19), current];
      futureRef.current = [];
      await _commitStyle(newStyle, current);
    },
    [_commitStyle],
  );

  const replaceStyle = useCallback(
    async (newStyle: TextStyle) => {
      const current = styleRef.current;
      if (current) {
        historyRef.current = [...historyRef.current.slice(-19), current];
      }
      futureRef.current = [];
      await _commitStyle(newStyle, current);
    },
    [_commitStyle],
  );

  const undo = useCallback(async () => {
    const current = styleRef.current;
    if (historyRef.current.length === 0 || !current) return;
    const prev = historyRef.current[historyRef.current.length - 1];
    historyRef.current = historyRef.current.slice(0, -1);
    futureRef.current = [current, ...futureRef.current.slice(0, 19)];
    await _commitStyle(prev, current);
  }, [_commitStyle]);

  const redo = useCallback(async () => {
    const current = styleRef.current;
    if (futureRef.current.length === 0 || !current) return;
    const [next, ...rest] = futureRef.current;
    futureRef.current = rest;
    historyRef.current = [...historyRef.current.slice(-19), current];
    await _commitStyle(next, current);
  }, [_commitStyle]);

  // Reset local state when the slide changes — backend is the source of truth
  useEffect(() => {
    setStyle(initialStyle);
    historyRef.current = [];
    futureRef.current = [];
  }, [initialStyle]);

  return {
    style,
    updateStyle,
    replaceStyle,
    isUpdating,
    undo,
    redo,
  };
}
