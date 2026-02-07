import { useState, useEffect, useRef, useCallback } from 'react';
import type { Session, BoxStyle, TextStyle } from '../types';
import * as api from '../services/api';
import { getErrorMessage } from '../utils/error';

interface Stage4Props {
  sessionId: string;
  session: Session | null;
  loading: boolean;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  updateSession: (session: Session) => void;
  onBack: () => void;
}

type SelectedBox = 'title' | 'body';

const FONTS = ['Inter', 'Roboto', 'Montserrat', 'Oswald', 'Poppins', 'Lato'];
const FONT_SIZES = [24, 28, 32, 36, 40, 48, 56, 64, 72, 80, 88, 96, 108, 120];

/** Deep-clone a style object (plain JSON, no methods). */
function cloneStyle(s: TextStyle): TextStyle {
  return JSON.parse(JSON.stringify(s));
}

export default function Stage4({
  sessionId,
  session,
  loading,
  setLoading,
  setError,
  updateSession,
  onBack,
}: Stage4Props) {
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
      if (currentSlide.style) {
        setLocalStyle(cloneStyle(currentSlide.style));
        dirtyStyleRef.current = false;
      }
      setLocalTitle(currentSlide.text.title);
      setLocalBody(currentSlide.text.body);
      dirtyTextRef.current = false;
      seededSlideRef.current = selectedSlide;
    }
  }, [selectedSlide, currentSlide]);

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
  // These flush functions read from latestRef to avoid stale closures.
  // Without this, the debounce timer would capture old values and lose
  // the most recent edit (e.g. a newline typed right before the user pauses).
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

  /** Schedule a debounced style sync + render. */
  const scheduleSyncAndRender = useCallback(() => {
    if (syncTimerRef.current) clearTimeout(syncTimerRef.current);
    if (renderTimerRef.current) clearTimeout(renderTimerRef.current);

    syncTimerRef.current = setTimeout(async () => {
      await flushStyleToBackend();
      renderTimerRef.current = setTimeout(renderSlide, 100);
    }, 1000);
  }, [flushStyleToBackend, renderSlide]);

  /** Schedule a debounced text sync + render. */
  const scheduleTextSyncAndRender = useCallback(() => {
    if (textSyncTimerRef.current) clearTimeout(textSyncTimerRef.current);
    if (renderTimerRef.current) clearTimeout(renderTimerRef.current);

    textSyncTimerRef.current = setTimeout(async () => {
      await flushTextToBackend();
      renderTimerRef.current = setTimeout(renderSlide, 100);
    }, 1000);
  }, [flushTextToBackend, renderSlide]);

  /** Apply a partial update to local style. No API calls — just setState. */
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
          (next as Record<string, unknown>)[key] = value;
        }
      }
      return next;
    });
    dirtyStyleRef.current = true;
    scheduleSyncAndRender();
  }, [scheduleSyncAndRender]);

  /** Update local text. No API calls — just setState. */
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

  // Flush before leaving Stage 4 (Back button)
  const handleBack = useCallback(async () => {
    // Cancel pending timers
    if (syncTimerRef.current) clearTimeout(syncTimerRef.current);
    if (renderTimerRef.current) clearTimeout(renderTimerRef.current);
    if (textSyncTimerRef.current) clearTimeout(textSyncTimerRef.current);

    const { sessionId: sid, selectedSlide: idx, localStyle: s, localTitle: t, localBody: b } = latestRef.current;

    // Flush dirty style
    if (dirtyStyleRef.current && s) {
      try {
        await api.updateStyle(sid, idx, s as unknown as Record<string, unknown>);
        dirtyStyleRef.current = false;
      } catch { /* best effort */ }
    }

    // Flush dirty text and update session so other stages see the changes
    if (dirtyTextRef.current) {
      try {
        const sess = await api.updateSlideText(sid, idx, t ?? undefined, b);
        dirtyTextRef.current = false;
        updateSession(sess);
      } catch { /* best effort */ }
    }

    onBack();
  }, [updateSession, onBack]);

  // Flush before leaving the slide (changing selected slide)
  const handleSlideChange = useCallback(async (index: number) => {
    // Cancel pending timers
    if (syncTimerRef.current) clearTimeout(syncTimerRef.current);
    if (renderTimerRef.current) clearTimeout(renderTimerRef.current);
    if (textSyncTimerRef.current) clearTimeout(textSyncTimerRef.current);

    const wasDirty = dirtyStyleRef.current || dirtyTextRef.current;

    // Flush any dirty state (reads from latestRef so always up-to-date)
    if (dirtyStyleRef.current) await flushStyleToBackend();
    if (dirtyTextRef.current) await flushTextToBackend();

    if (wasDirty) {
      // Fire-and-forget render for the old slide
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
    // Flush any pending local changes first
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
    // Don't start drag if clicking inside an editable area
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
              <svg className="animate-spin h-3 w-3" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
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

// --- Sub-components ---

interface TextBoxOverlayProps {
  text: string;
  box: BoxStyle;
  fontFamily: string;
  fontWeight: number;
  fontSize: number;
  textColor: string;
  alignment: 'left' | 'center' | 'right';
  stroke: { enabled: boolean; width_px: number; color: string };
  isSelected: boolean;
  onMouseDown: (e: React.MouseEvent) => void;
  onResizeMouseDown?: (corner: string, e: React.MouseEvent) => void;
  onTextChange: (text: string) => void;
}

function TextBoxOverlay({
  text,
  box,
  fontFamily,
  fontWeight,
  fontSize,
  textColor,
  alignment,
  stroke,
  isSelected,
  onMouseDown,
  onResizeMouseDown,
  onTextChange,
}: TextBoxOverlayProps) {
  const editRef = useRef<HTMLDivElement>(null);

  // Scale font size to preview — the canvas is ~400px wide, real image is 1080px
  const scaleFactor = 400 / 1080;
  const previewFontSize = Math.max(8, Math.round(fontSize * scaleFactor));

  const strokeStyle = stroke.enabled
    ? { WebkitTextStroke: `${stroke.width_px}px ${stroke.color}`, paintOrder: 'stroke fill' as const }
    : {};

  // Seed contentEditable text once when it becomes selected (DOM owns it after that)
  const wasSelectedRef = useRef(false);
  useEffect(() => {
    if (isSelected && !wasSelectedRef.current && editRef.current) {
      editRef.current.innerText = text;
    }
    wasSelectedRef.current = isSelected;
  }, [isSelected, text]);

  const handleInput = () => {
    if (editRef.current) {
      onTextChange(editRef.current.innerText);
    }
  };

  return (
    <div
      className={`absolute cursor-move ${isSelected ? 'z-10' : 'z-0'}`}
      style={{
        left: `${box.x_pct * 100}%`,
        top: `${box.y_pct * 100}%`,
        width: `${box.w_pct * 100}%`,
        height: `${box.h_pct * 100}%`,
        outline: isSelected ? '2px solid #3b82f6' : '1px dashed rgba(156,163,175,0.5)',
        outlineOffset: '-1px',
        borderRadius: '4px',
        boxSizing: 'border-box',
      }}
      onMouseDown={onMouseDown}
    >
      {/* Text content */}
      <div
        className="w-full h-full overflow-hidden flex items-center"
        style={{
          padding: `${box.padding_pct * 100}%`,
          fontFamily,
          fontWeight,
          fontSize: `${previewFontSize}px`,
          lineHeight: 1.2,
          color: textColor,
          textAlign: alignment,
          wordBreak: 'break-word',
          ...strokeStyle,
        }}
      >
        {isSelected ? (
          <div
            ref={editRef}
            className="w-full cursor-text"
            contentEditable
            suppressContentEditableWarning
            onInput={handleInput}
            onMouseDown={(e) => e.stopPropagation()}
            style={{ outline: 'none', whiteSpace: 'pre-wrap' }}
          />
        ) : (
          <div className="w-full" style={{ whiteSpace: 'pre-wrap' }}>{text}</div>
        )}
      </div>

      {/* Resize handles (only when selected) */}
      {isSelected && onResizeMouseDown && (
        <>
          <ResizeHandle corner="tl" onMouseDown={onResizeMouseDown} />
          <ResizeHandle corner="tr" onMouseDown={onResizeMouseDown} />
          <ResizeHandle corner="bl" onMouseDown={onResizeMouseDown} />
          <ResizeHandle corner="br" onMouseDown={onResizeMouseDown} />
        </>
      )}
    </div>
  );
}

interface ResizeHandleProps {
  corner: string;
  onMouseDown: (corner: string, e: React.MouseEvent) => void;
}

function ResizeHandle({ corner, onMouseDown }: ResizeHandleProps) {
  const positionClasses: Record<string, string> = {
    tl: '-top-1 -left-1 cursor-nw-resize',
    tr: '-top-1 -right-1 cursor-ne-resize',
    bl: '-bottom-1 -left-1 cursor-sw-resize',
    br: '-bottom-1 -right-1 cursor-se-resize',
  };

  return (
    <div
      className={`absolute w-2.5 h-2.5 bg-white border-2 border-blue-500 rounded-full ${positionClasses[corner]}`}
      onMouseDown={(e) => onMouseDown(corner, e)}
    />
  );
}

function AlignIcon({ align }: { align: 'left' | 'center' | 'right' }) {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
      {align === 'left' && (
        <>
          <rect x="1" y="2" width="14" height="1.5" rx="0.5" />
          <rect x="1" y="6" width="10" height="1.5" rx="0.5" />
          <rect x="1" y="10" width="12" height="1.5" rx="0.5" />
          <rect x="1" y="14" width="8" height="1.5" rx="0.5" />
        </>
      )}
      {align === 'center' && (
        <>
          <rect x="1" y="2" width="14" height="1.5" rx="0.5" />
          <rect x="3" y="6" width="10" height="1.5" rx="0.5" />
          <rect x="2" y="10" width="12" height="1.5" rx="0.5" />
          <rect x="4" y="14" width="8" height="1.5" rx="0.5" />
        </>
      )}
      {align === 'right' && (
        <>
          <rect x="1" y="2" width="14" height="1.5" rx="0.5" />
          <rect x="5" y="6" width="10" height="1.5" rx="0.5" />
          <rect x="3" y="10" width="12" height="1.5" rx="0.5" />
          <rect x="7" y="14" width="8" height="1.5" rx="0.5" />
        </>
      )}
    </svg>
  );
}
