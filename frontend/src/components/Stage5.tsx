import { useState, useEffect, useRef, useCallback } from 'react';
import * as api from '../services/api';
import { getErrorMessage } from '../utils/error';
import { useSessionContext } from '../contexts/SessionContext';
import { useAppConfig } from '../hooks/useAppConfig';
import { useDragResize } from '../hooks/useDragResize';
import { useStyleManager } from '../hooks/useStyleManager';
import { useApiAction } from '../hooks/useApiAction';
import CarouselCanvas from './CarouselCanvas';
import SlideThumbnails from './SlideThumbnails';
import StyleToolbar from './StyleToolbar';

type SelectedBox = 'title' | 'body';


export default function Stage5() {
  const {
    sessionId,
    session,
    loading,
    setError,
    updateSession,
    onBack,
  } = useSessionContext();

  const config = useAppConfig();
  const [selectedSlide, setSelectedSlide] = useState(0);
  const [selectedBox, setSelectedBox] = useState<SelectedBox>('title');

  const containerRef = useRef<HTMLDivElement>(null);

  const slides = session?.slides || [];
  const currentSlide = slides[selectedSlide];

  // Style management using useStyleManager hook
  const { style, updateStyle, isUpdating: styleUpdating } = useStyleManager({
    sessionId,
    slideIndex: selectedSlide,
    initialStyle: currentSlide?.style || null,
    config
  });

  // Local text state
  const [localTitle, setLocalTitle] = useState<string | null>(currentSlide?.text.title || null);
  const [localBody, setLocalBody] = useState<string>(currentSlide?.text.body || '');
  const textSyncTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const hasTitle = !!(localTitle);

  // Use ApiAction for renderSlide (defined early — used by scheduleTextSyncAndRender)
  const { execute: renderSlide, isLoading: rendering } = useApiAction({
    action: () => api.applyTextToSlide(sessionId, selectedSlide),
    onSuccess: (newSession) => updateSession(newSession),
    onError: (error) => setError(error)
  });

  // Sync text to backend
  const syncTextToBackend = useCallback(async () => {
    try {
      const sess = await api.updateSlideText(sessionId, selectedSlide, localTitle ?? undefined, localBody);
      updateSession(sess);
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to save text'));
    }
  }, [sessionId, selectedSlide, localTitle, localBody, updateSession, setError]);

  // Schedule text sync and render
  const scheduleTextSyncAndRender = useCallback(() => {
    if (textSyncTimerRef.current) {
      clearTimeout(textSyncTimerRef.current);
    }
    textSyncTimerRef.current = setTimeout(async () => {
      await syncTextToBackend();
      // Schedule render after sync completes
      setTimeout(() => {
        renderSlide();
      }, 100);
    }, 1000);
  }, [syncTextToBackend, renderSlide]);

  // Text change handler
  const handleTextChange = useCallback((which: 'title' | 'body', text: string) => {
    if (which === 'title') {
      setLocalTitle(text);
    } else {
      setLocalBody(text);
    }
    scheduleTextSyncAndRender();
  }, [scheduleTextSyncAndRender]);

  // Cleanup timer
  useEffect(() => {
    return () => {
      if (textSyncTimerRef.current) {
        clearTimeout(textSyncTimerRef.current);
      }
    };
  }, []);

  // Update local text when selected slide changes
  useEffect(() => {
    setLocalTitle(currentSlide?.text.title || null);
    setLocalBody(currentSlide?.text.body || '');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedSlide]);

  // If no title, auto-select body
  useEffect(() => {
    if (!hasTitle && selectedBox === 'title') {
      setSelectedBox('body');
    }
  }, [hasTitle, selectedBox]);

  // Auto-apply to all slides on first render
  useEffect(() => {
    if (slides.length > 0 && slides.some((s) => s.image_data && !s.final_image)) {
      applyToAll();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Auto-render when style changes
  const renderTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    if (renderTimerRef.current) {
      clearTimeout(renderTimerRef.current);
    }

    // Schedule render after a short delay when style is updating
    if (styleUpdating) {
      renderTimerRef.current = setTimeout(() => {
        renderSlide();
      }, 100);
    }

    return () => {
      if (renderTimerRef.current) {
        clearTimeout(renderTimerRef.current);
      }
    };
  }, [styleUpdating, renderSlide]);

  const handleBack = useCallback(async () => {
    // Sync any pending text changes before navigating back
    if (textSyncTimerRef.current) {
      clearTimeout(textSyncTimerRef.current);
      await syncTextToBackend();
      // Also trigger render for current slide before leaving
      await renderSlide();
    }
    onBack();
  }, [syncTextToBackend, renderSlide, onBack]);

  const handleSlideChange = useCallback(async (index: number) => {
    // Sync any pending text changes before switching slides
    if (textSyncTimerRef.current) {
      clearTimeout(textSyncTimerRef.current);
      await syncTextToBackend();
      // Also trigger render for current slide before switching
      await renderSlide();
    }
    setSelectedSlide(index);
  }, [syncTextToBackend, renderSlide]);

  const { handleBoxMouseDown, handleResizeMouseDown } = useDragResize({
    containerRef,
    style,
    selectedBox,
    setSelectedBox,
    updateLocalStyle: updateStyle,
  });

  // Use ApiAction for applyToAll
  const { execute: applyToAll, isLoading: applyingToAll } = useApiAction({
    action: async () => {
      if (!style) throw new Error('No style to apply');
      const styleDict = style as unknown as Record<string, unknown>;
      await api.applyStyleToAll(sessionId, styleDict);
      return await api.applyTextToAll(sessionId);
    },
    onSuccess: (newSession) => updateSession(newSession),
    onError: (error) => setError(error)
  });

  const handleExport = () => {
    window.open(api.getExportZipUrl(sessionId), '_blank');
  };

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
        <StyleToolbar
          style={style}
          selectedBox={selectedBox}
          hasTitle={hasTitle}
          loading={loading || applyingToAll}
          setSelectedBox={setSelectedBox}
          updateLocalStyle={updateStyle}
          onApplyToAll={applyToAll}
        />
      )}

      {/* Canvas */}
      <CarouselCanvas
        containerRef={containerRef}
        currentSlide={currentSlide}
        selectedSlide={selectedSlide}
        style={style}
        localTitle={localTitle}
        localBody={localBody}
        selectedBox={selectedBox}
        rendering={rendering}
        handleBoxMouseDown={handleBoxMouseDown}
        handleResizeMouseDown={handleResizeMouseDown}
        handleTextChange={handleTextChange}
      />

      {/* Slide thumbnails */}
      <SlideThumbnails
        slides={slides}
        selectedSlide={selectedSlide}
        onSlideChange={handleSlideChange}
      />
    </div>
  );
}
