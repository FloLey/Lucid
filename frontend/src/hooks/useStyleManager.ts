import { useState, useCallback, useEffect } from 'react';
import type { TextStyle, AppConfig } from '../types';
import * as api from '../services/api';

interface UseStyleManagerOptions {
  projectId: string;
  slideIndex: number;
  initialStyle: TextStyle | null;
  config?: AppConfig | null;
}

export function useStyleManager({
  projectId,
  slideIndex,
  initialStyle,
  config
}: UseStyleManagerOptions) {
  const [style, setStyle] = useState<TextStyle | null>(initialStyle);
  const [isUpdating, setIsUpdating] = useState(false);

  // Apply config defaults to style
  const applyConfigDefaults = useCallback((baseStyle: TextStyle): TextStyle => {
    const cloned = JSON.parse(JSON.stringify(baseStyle));

    if (config) {
      if (cloned.font_family === 'Inter' && config.style.default_font_family !== 'Inter') {
        cloned.font_family = config.style.default_font_family;
      }
      if (cloned.font_weight === 700 && config.style.default_font_weight !== 700) {
        cloned.font_weight = config.style.default_font_weight;
      }
      if (cloned.font_size_px === 72 && config.style.default_font_size_px !== 72) {
        cloned.font_size_px = config.style.default_font_size_px;
      }
      if (cloned.text_color === '#FFFFFF' && config.style.default_text_color !== '#FFFFFF') {
        cloned.text_color = config.style.default_text_color;
      }
      if (cloned.alignment === 'center' && config.style.default_alignment !== 'center') {
        cloned.alignment = config.style.default_alignment as 'left' | 'center' | 'right';
      }
      if (!cloned.stroke.enabled && config.style.default_stroke_enabled) {
        cloned.stroke.enabled = config.style.default_stroke_enabled;
        cloned.stroke.width_px = config.style.default_stroke_width_px;
        cloned.stroke.color = config.style.default_stroke_color;
      }
    }

    return cloned;
  }, [config]);

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

  const resetToDefaults = useCallback(() => {
    if (!initialStyle) return;
    const defaultStyle = applyConfigDefaults(initialStyle);
    setStyle(defaultStyle);
    // Optionally sync to backend immediately
    updateStyle(defaultStyle).catch(console.error);
  }, [initialStyle, applyConfigDefaults, updateStyle]);

  // Update when slide changes
  useEffect(() => {
    if (initialStyle) {
      const styledWithDefaults = applyConfigDefaults(initialStyle);
      setStyle(styledWithDefaults);
    } else {
      setStyle(null);
    }
  }, [initialStyle, applyConfigDefaults]);

  return {
    style,
    updateStyle,
    resetToDefaults,
    isUpdating,
    applyConfigDefaults
  };
}