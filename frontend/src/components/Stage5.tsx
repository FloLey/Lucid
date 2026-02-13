import { useState, useEffect, useRef, useCallback } from 'react';
import type { BoxStyle, TextStyle } from '../types';
import * as api from '../services/api';
import { getErrorMessage } from '../utils/error';
import { useSessionContext } from '../contexts/SessionContext';
import { useAppConfig } from '../hooks/useAppConfig';
import { FONTS, FONT_SIZES } from '../constants';
import Spinner from './Spinner';
import TextBoxOverlay from './TextBoxOverlay';
import AlignIcon from './AlignIcon';

type SelectedBox = 'title' | 'body';

/** Deep-clone a style object (plain JSON, no methods). */
function cloneStyle(s: TextStyle): TextStyle {
  return JSON.parse(JSON.stringify(s));
}

export default function Stage5() {
  const {
    sessionId,
    session,
    loading,
    setLoading,
    setError,
    updateSession,
    onBack,
  } = useSessionContext();

  const config = useAppConfig();
  const [selectedSlide, setSelectedSlide] = useState(0);
  const [selectedBox, setSelectedBox] = useState<SelectedBox>('title');
  const [rendering, setRendering] = useState(false);

  // --- Local style state (for instant preview, no API calls) ---
  const [localStyle, setLocalStyle] = useState<TextStyle | null>(null);
  const dirtyStyleRef = useRef(false);
  const syncTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const renderTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // --- Local text state (for inline editing) ---
  const [localTitle, setLocalTitle] = useState<string | null>(null);
  const [localBody, setLocalBody] = useState<string>('');
  const dirtyTextRef = useRef(false);
  const textSyncTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Drag state
  const [dragging, setDragging] = useState(false);
  const dragStartRef = useRef<{ mouseX: number; mouseY: number; boxX: number; boxY: number } | null>(null);

  // Resize state
  const [resizing, setResizing] = useState(false);
  const resizeStartRef = useRef<{ mouseX: number; mouseY: number; boxW: number; boxH: number; boxX: number; boxY: number; corner: string } | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);

  const slides = session?.slides || [];
  const currentSlide = slides[selectedSlide];
  const hasTitle = !!(localTitle);

  // The style used for preview — local if available, otherwise from server
  const style = localStyle ?? currentSlide?.style ?? null;

  // Seed local style + text only when switching slides
  const seededSlideRef = useRef<number | null>(null);
  useEffect(() => {
    if (currentSlide && seededSlideRef.current !== selectedSlide) {
      setLocalTitle(currentSlide.text.title);
      setLocalBody(currentSlide.text.body);
      dirtyTextRef.current = false;

      if (currentSlide.style) {
        const cloned = cloneStyle(currentSlide.style);

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

        setLocalStyle(cloned);
        dirtyStyleRef.current = false;
      }

      seededSlideRef.current = selectedSlide;
    }
  }, [selectedSlide, currentSlide, config]);

  // If no title, auto-select body
  useEffect(() => {
    if (!hasTitle && selectedBox === 'title') {
      setSelectedBox('body');
    }
  }, [hasTitle, selectedBox]);

  // Auto-apply to all slides on first render
  useEffect(() => {
    if (slides.length > 0 && slides.some((s) => s.image_data && !s.final_image)) {
      const applyAll = async () => {
        setLoading(true);
        try {
          const sess = await api.applyTextToAll(sessionId);
          updateSession(sess);
        } catch (err) {
          setError(getErrorMessage(err, 'Failed to apply typography'));
        } finally {
          setLoading(false);
        }
      };
      applyAll();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // --- Backend sync (debounced) ---
  const flushStyleToBackend = useCallback(async () => {
    if (!dirtyStyleRef.current) return;
    const { sessionId: sid, selectedSlide: idx, localStyle: s } = latestRef.current;
    if (!s) return;
    dirtyStyleRef.current = false;
    try {
      await api.updateStyle(sid, idx, s as unknown as Record<string, unknown>);
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to save style'));
    }
  }, [setError]);

  const flushTextToBackend = useCallback(async () => {
    if (!dirtyTextRef.current) return;
    const { sessionId: sid, selectedSlide: idx, localTitle: t, localBody: b } = latestRef.current;
    dirtyTextRef.current = false;
    try {
      const sess = await api.updateSlideText(sid, idx, t ?? undefined, b);
      updateSession(sess);
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to save text'));
    }
  }, [setError, updateSession]);

  const renderSlide = useCallback(async () => {
    setRendering(true);
    try {
      const sess = await api.applyTextToSlide(sessionId, selectedSlide);
      updateSession(sess);
    } catch (err) {
      setError(getErrorMessage(err, `Failed to render slide ${selectedSlide + 1}`));
    } finally {
      setRendering(false);
    }
  }, [sessionId, selectedSlide, updateSession, setError]);

  const scheduleSyncAndRender = useCallback(() => {
    if (syncTimerRef.current) clearTimeout(syncTimerRef.current);
    if (renderTimerRef.current) clearTimeout(renderTimerRef.current);

    syncTimerRef.current = setTimeout(async () => {
      await flushStyleToBackend();
      renderTimerRef.current = setTimeout(renderSlide, 100);
    }, 1000);
  }, [flushStyleToBackend, renderSlide]);

  const scheduleTextSyncAndRender = useCallback(() => {
    if (textSyncTimerRef.current) clearTimeout(textSyncTimerRef.current);
    if (renderTimerRef.current) clearTimeout(renderTimerRef.current);

    textSyncTimerRef.current = setTimeout(async () => {
      await flushTextToBackend();
      renderTimerRef.current = setTimeout(renderSlide, 100);
    }, 1000);
  }, [flushTextToBackend, renderSlide]);

  const updateLocalStyle = useCallback((updates: Record<string, unknown>) => {
    setLocalStyle((prev) => {
      if (!prev) return prev;
      const next = cloneStyle(prev);

      for (const [key, value] of Object.entries(updates)) {
        if (key === 'title_box' || key === 'body_box') {
          const box = next[key] as BoxStyle;
          Object.assign(box, value);
        } else if (key === 'stroke') {
          Object.assign(next.stroke, value);
        } else if (key === 'shadow') {
          Object.assign(next.shadow, value);
        } else {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          (next as any)[key] = value;
        }
      }
      return next;
    });
    dirtyStyleRef.current = true;
    scheduleSyncAndRender();
  }, [scheduleSyncAndRender]);

  const handleTextChange = useCallback((which: 'title' | 'body', text: string) => {
    if (which === 'title') {
      setLocalTitle(text);
    } else {
      setLocalBody(text);
    }
    dirtyTextRef.current = true;
    scheduleTextSyncAndRender();
  }, [scheduleTextSyncAndRender]);

  // Keep a ref to latest flush-relevant data for the unmount cleanup
  const latestRef = useRef({ sessionId, selectedSlide, localTitle, localBody, localStyle });
  useEffect(() => {
    latestRef.current = { sessionId, selectedSlide, localTitle, localBody, localStyle };
  });

  // Cleanup: cancel timers and fire-and-forget flush any dirty data
  useEffect(() => {
    return () => {
      if (syncTimerRef.current) clearTimeout(syncTimerRef.current);
      if (renderTimerRef.current) clearTimeout(renderTimerRef.current);
      if (textSyncTimerRef.current) clearTimeout(textSyncTimerRef.current);

      const { sessionId: sid, selectedSlide: idx, localTitle: t, localBody: b, localStyle: s } = latestRef.current;
      if (dirtyTextRef.current) {
        api.updateSlideText(sid, idx, t ?? undefined, b).catch(() => {});
      }
      if (dirtyStyleRef.current && s) {
        api.updateStyle(sid, idx, s as unknown as Record<string, unknown>).catch(() => {});
      }
    };
  }, []);

  const handleBack = useCallback(async () => {
    if (syncTimerRef.current) clearTimeout(syncTimerRef.current);
    if (renderTimerRef.current) clearTimeout(renderTimerRef.current);
    if (textSyncTimerRef.current) clearTimeout(textSyncTimerRef.current);

    const { sessionId: sid, selectedSlide: idx, localStyle: s, localTitle: t, localBody: b } = latestRef.current;

    if (dirtyStyleRef.current && s) {
      try {
        await api.updateStyle(sid, idx, s as unknown as Record<string, unknown>);
        dirtyStyleRef.current = false;
      } catch { /* best effort */ }
    }

    if (dirtyTextRef.current) {
      try {
        const sess = await api.updateSlideText(sid, idx, t ?? undefined, b);
        dirtyTextRef.current = false;
        updateSession(sess);
      } catch { /* best effort */ }
    }

    onBack();
  }, [updateSession, onBack]);

  const handleSlideChange = useCallback(async (index: number) => {
    if (syncTimerRef.current) clearTimeout(syncTimerRef.current);
    if (renderTimerRef.current) clearTimeout(renderTimerRef.current);
    if (textSyncTimerRef.current) clearTimeout(textSyncTimerRef.current);

    const wasDirty = dirtyStyleRef.current || dirtyTextRef.current;

    if (dirtyStyleRef.current) await flushStyleToBackend();
    if (dirtyTextRef.current) await flushTextToBackend();

    if (wasDirty) {
      const { sessionId: sid, selectedSlide: idx } = latestRef.current;
      api.applyTextToSlide(sid, idx).then(updateSession).catch(() => {});
    }

    seededSlideRef.current = null;
    setSelectedSlide(index);
  }, [flushStyleToBackend, flushTextToBackend, updateSession]);

  const getActiveFontSize = (): number => {
    if (!style) return 48;
    return selectedBox === 'title' ? style.font_size_px : style.body_font_size_px;
  };

  const handleFontSizeChange = (size: number) => {
    if (selectedBox === 'title') {
      updateLocalStyle({ font_size_px: size });
    } else {
      updateLocalStyle({ body_font_size_px: size });
    }
  };

  const handleApplyToAll = async () => {
    if (!style) return;
    if (syncTimerRef.current) clearTimeout(syncTimerRef.current);
    if (textSyncTimerRef.current) clearTimeout(textSyncTimerRef.current);
    if (dirtyStyleRef.current) await flushStyleToBackend();
    if (dirtyTextRef.current) await flushTextToBackend();

    setLoading(true);
    setError(null);
    try {
      const styleDict = style as unknown as Record<string, unknown>;
      await api.applyStyleToAll(sessionId, styleDict);
      const sess = await api.applyTextToAll(sessionId);
      updateSession(sess);
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to apply style to all slides'));
    } finally {
      setLoading(false);
    }
  };

  const handleExport = () => {
    window.open(api.getExportZipUrl(sessionId), '_blank');
  };

  // --- Drag handlers ---
  const getContainerRect = () => containerRef.current?.getBoundingClientRect();

  const handleBoxMouseDown = (box: SelectedBox, e: React.MouseEvent) => {
    const target = e.target as HTMLElement;
    if (target.getAttribute('contenteditable') === 'true') return;

    e.preventDefault();
    e.stopPropagation();
    setSelectedBox(box);
    const rect = getContainerRect();
    if (!rect || !style) return;

    const bx = box === 'title' ? style.title_box : style.body_box;
    dragStartRef.current = {
      mouseX: e.clientX,
      mouseY: e.clientY,
      boxX: bx.x_pct,
      boxY: bx.y_pct,
    };
    setDragging(true);
  };

  const handleResizeMouseDown = (corner: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const rect = getContainerRect();
    if (!rect || !style) return;

    const bx = selectedBox === 'title' ? style.title_box : style.body_box;
    resizeStartRef.current = {
      mouseX: e.clientX,
      mouseY: e.clientY,
      boxW: bx.w_pct,
      boxH: bx.h_pct,
      boxX: bx.x_pct,
      boxY: bx.y_pct,
      corner,
    };
    setResizing(true);
  };

  useEffect(() => {
    if (!dragging && !resizing) return;

    const handleMouseMove = (e: MouseEvent) => {
      const rect = getContainerRect();
      if (!rect) return;

      if (dragging && dragStartRef.current) {
        const dx = (e.clientX - dragStartRef.current.mouseX) / rect.width;
        const dy = (e.clientY - dragStartRef.current.mouseY) / rect.height;
        const newX = Math.max(0, Math.min(1, dragStartRef.current.boxX + dx));
        const newY = Math.max(0, Math.min(1, dragStartRef.current.boxY + dy));
        const key = selectedBox === 'title' ? 'title_box' : 'body_box';
        updateLocalStyle({ [key]: { x_pct: newX, y_pct: newY } });
      }

      if (resizing && resizeStartRef.current) {
        const s = resizeStartRef.current;
        const dx = (e.clientX - s.mouseX) / rect.width;
        const dy = (e.clientY - s.mouseY) / rect.height;

        let newX = s.boxX;
        let newY = s.boxY;
        let newW = s.boxW;
        let newH = s.boxH;

        if (s.corner.includes('r')) {
          newW = Math.max(0.1, Math.min(1 - s.boxX, s.boxW + dx));
        }
        if (s.corner.includes('l')) {
          const maxDx = s.boxW - 0.1;
          const clampedDx = Math.max(-s.boxX, Math.min(maxDx, dx));
          newX = s.boxX + clampedDx;
          newW = s.boxW - clampedDx;
        }
        if (s.corner.includes('b')) {
          newH = Math.max(0.05, Math.min(1 - s.boxY, s.boxH + dy));
        }
        if (s.corner.includes('t')) {
          const maxDy = s.boxH - 0.05;
          const clampedDy = Math.max(-s.boxY, Math.min(maxDy, dy));
          newY = s.boxY + clampedDy;
          newH = s.boxH - clampedDy;
        }

        const key = selectedBox === 'title' ? 'title_box' : 'body_box';
        updateLocalStyle({ [key]: { x_pct: newX, y_pct: newY, w_pct: newW, h_pct: newH } });
      }
    };

    const handleMouseUp = () => {
      setDragging(false);
      setResizing(false);
      dragStartRef.current = null;
      resizeStartRef.current = null;
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [dragging, resizing, selectedBox, updateLocalStyle]);

  const hasFinalImages = slides.some((s) => s.final_image);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={handleBack}
            className="px-3 py-1.5 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
          >
            &larr; Back
          </button>
          <h2 className="text-lg font-semibold text-gray-900">Typography & Layout</h2>
        </div>
        {hasFinalImages && (
          <button
            onClick={handleExport}
            className="px-4 py-2 bg-lucid-600 text-white font-medium rounded-lg hover:bg-lucid-700 transition-colors"
          >
            Export ZIP
          </button>
        )}
      </div>

      {/* Toolbar */}
      {style && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 px-4 py-3">
          <div className="flex flex-wrap items-center gap-3">
            {/* Selected box indicator */}
            {hasTitle && (
              <div className="flex items-center gap-1">
                <span className="text-xs text-gray-500 mr-1">Editing:</span>
                <button
                  onClick={() => setSelectedBox('title')}
                  className={`px-2 py-1 text-xs rounded font-medium transition-colors ${
                    selectedBox === 'title'
                      ? 'bg-blue-100 text-blue-700 ring-1 ring-blue-300'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  Title
                </button>
                <button
                  onClick={() => setSelectedBox('body')}
                  className={`px-2 py-1 text-xs rounded font-medium transition-colors ${
                    selectedBox === 'body'
                      ? 'bg-blue-100 text-blue-700 ring-1 ring-blue-300'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  Body
                </button>
              </div>
            )}

            <div className="w-px h-6 bg-gray-200" />

            {/* Font family */}
            <select
              value={style.font_family}
              onChange={(e) => updateLocalStyle({ font_family: e.target.value })}
              className="text-xs border border-gray-300 rounded px-2 py-1.5 bg-white"
              style={{ fontFamily: style.font_family }}
            >
              {FONTS.map((f) => (
                <option key={f} value={f} style={{ fontFamily: f }}>{f}</option>
              ))}
            </select>

            {/* Font size */}
            <select
              value={getActiveFontSize()}
              onChange={(e) => handleFontSizeChange(Number(e.target.value))}
              className="text-xs border border-gray-300 rounded px-2 py-1.5 bg-white w-16"
            >
              {FONT_SIZES.map((s) => (
                <option key={s} value={s}>{s}px</option>
              ))}
            </select>

            {/* Color picker */}
            <div className="relative">
              <input
                type="color"
                value={style.text_color.slice(0, 7)}
                onChange={(e) => updateLocalStyle({ text_color: e.target.value })}
                className="w-7 h-7 rounded cursor-pointer border border-gray-300"
                title="Text color"
              />
            </div>

            <div className="w-px h-6 bg-gray-200" />

            {/* Alignment */}
            {(['left', 'center', 'right'] as const).map((align) => (
              <button
                key={align}
                onClick={() => updateLocalStyle({ alignment: align })}
                className={`p-1.5 rounded transition-colors ${
                  style.alignment === align
                    ? 'bg-lucid-100 text-lucid-700'
                    : 'text-gray-500 hover:bg-gray-100'
                }`}
                title={`Align ${align}`}
              >
                <AlignIcon align={align} />
              </button>
            ))}

            <div className="w-px h-6 bg-gray-200" />

            {/* Stroke toggle */}
            <button
              onClick={() => updateLocalStyle({ stroke: { enabled: !style.stroke.enabled } })}
              className={`px-2 py-1 text-xs rounded font-medium transition-colors ${
                style.stroke.enabled
                  ? 'bg-gray-800 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
              title="Toggle stroke"
            >
              Stroke
            </button>

            <div className="flex-1" />

            {/* Apply to All */}
            <button
              onClick={handleApplyToAll}
              disabled={loading}
              className="px-3 py-1.5 text-xs bg-white border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
            >
              {loading ? 'Applying...' : 'Apply to All'}
            </button>
          </div>
        </div>
      )}

      {/* Canvas area */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <div
          ref={containerRef}
          className="relative aspect-[4/5] max-w-md mx-auto bg-gray-100 rounded-lg overflow-hidden select-none"
        >
          {/* Background image */}
          {currentSlide?.image_data && (
            <img
              src={`data:image/png;base64,${currentSlide.image_data}`}
              alt={`Slide ${selectedSlide + 1} background`}
              className="absolute inset-0 w-full h-full object-cover"
              draggable={false}
            />
          )}

          {/* Title box overlay */}
          {hasTitle && style && (
            <TextBoxOverlay
              text={localTitle!}
              box={style.title_box}
              fontFamily={style.font_family}
              fontWeight={style.font_weight}
              fontSize={style.font_size_px}
              textColor={style.text_color}
              alignment={style.alignment as 'left' | 'center' | 'right'}
              stroke={style.stroke}
              isSelected={selectedBox === 'title'}
              onMouseDown={(e) => handleBoxMouseDown('title', e)}
              onResizeMouseDown={selectedBox === 'title' ? handleResizeMouseDown : undefined}
              onTextChange={(text) => handleTextChange('title', text)}
            />
          )}

          {/* Body box overlay */}
          {localBody && style && (
            <TextBoxOverlay
              text={localBody}
              box={style.body_box}
              fontFamily={style.font_family}
              fontWeight={Math.max(400, style.font_weight - 200)}
              fontSize={style.body_font_size_px}
              textColor={style.text_color}
              alignment={style.alignment as 'left' | 'center' | 'right'}
              stroke={style.stroke}
              isSelected={selectedBox === 'body'}
              onMouseDown={(e) => handleBoxMouseDown('body', e)}
              onResizeMouseDown={selectedBox === 'body' ? handleResizeMouseDown : undefined}
              onTextChange={(text) => handleTextChange('body', text)}
            />
          )}

          {/* No image placeholder */}
          {!currentSlide?.image_data && (
            <div className="absolute inset-0 flex items-center justify-center text-gray-400">
              No image
            </div>
          )}

          {/* Rendering indicator */}
          {rendering && (
            <div className="absolute top-2 right-2 flex items-center gap-1.5 bg-black/60 text-white text-xs px-2 py-1 rounded-full">
              <Spinner size="sm" />
              Rendering
            </div>
          )}
        </div>
      </div>

      {/* Slide thumbnails */}
      <div className="flex gap-2 overflow-x-auto pb-2">
        {slides.map((slide, index) => (
          <button
            key={index}
            onClick={() => handleSlideChange(index)}
            className={`flex-shrink-0 w-16 rounded-lg overflow-hidden border-2 transition-colors ${
              index === selectedSlide
                ? 'border-lucid-600'
                : 'border-transparent hover:border-gray-300'
            }`}
          >
            <div className="aspect-[4/5] bg-gray-100">
              {slide.final_image || slide.image_data ? (
                <img
                  src={`data:image/png;base64,${slide.final_image || slide.image_data}`}
                  alt={`Slide ${index + 1}`}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-xs text-gray-400">
                  {index + 1}
                </div>
              )}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
