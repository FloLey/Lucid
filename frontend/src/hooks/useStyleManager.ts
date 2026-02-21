import { useState, useCallback, useEffect } from 'react';
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

  const updateStyle = useCallback(async (updates: Partial<TextStyle>) => {
    if (!style) return;

    // Create a deep clone of the current style
    const newStyle = JSON.parse(JSON.stringify(style));

    // Apply updates, handling nested objects
    for (const [key, value] of Object.entries(updates)) {
      if (key === 'title_box' || key === 'body_box') {
        // Merge box updates
        Object.assign(newStyle[key], value);
      } else if (key === 'stroke' || key === 'shadow') {
        // Merge stroke or shadow updates
        Object.assign(newStyle[key], value);
      } else {
        // Simple property update
        (newStyle as Record<string, unknown>)[key] = value;
      }
    }

    setStyle(newStyle);

    setIsUpdating(true);
    try {
      await api.updateStyle(projectId, slideIndex, newStyle as unknown as Record<string, unknown>);
    } catch (error) {
      console.error('Failed to update style:', error);
      // Revert on error
      setStyle(style);
      throw error;
    } finally {
      setIsUpdating(false);
    }
  }, [projectId, slideIndex, style]);

  // Update when slide changes — backend is the source of truth for initial style
  useEffect(() => {
    setStyle(initialStyle);
  }, [initialStyle]);

  return {
    style,
    updateStyle,
    isUpdating,
  };
}