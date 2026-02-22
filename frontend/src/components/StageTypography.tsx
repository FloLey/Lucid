import { useState, useEffect, useRef, useCallback } from 'react';
import * as api from '../services/api';
import { useProject } from '../contexts/ProjectContext';
import { useDragResize } from '../hooks/useDragResize';
import { useStyleManager } from '../hooks/useStyleManager';
import { useApiAction } from '../hooks/useApiAction';
import { useDebouncedRender } from '../hooks/useDebouncedRender';
import CarouselCanvas from './CarouselCanvas';
import SlideThumbnails from './SlideThumbnails';
import StyleToolbar from './StyleToolbar';

type SelectedBox = 'title' | 'body';


export default function Stage5() {
  const {
    projectId,
    currentProject: project,
    stageLoading: loading,
    setError,
    updateProject,
    previousStage: onBack,
  } = useProject();

  const [selectedSlide, setSelectedSlide] = useState(0);
  const [selectedBox, setSelectedBox] = useState<SelectedBox>('title');

  const containerRef = useRef<HTMLDivElement>(null);

  const slides = project?.slides || [];
  const currentSlide = slides[selectedSlide];

  // Keep a ref to slides so effects can read the latest value without re-running
  const slidesRef = useRef(slides);
  slidesRef.current = slides;

  // Style management using useStyleManager hook
  const { style, updateStyle, isUpdating: styleUpdating } = useStyleManager({
    projectId,
    slideIndex: selectedSlide,
    initialStyle: currentSlide?.style || null,
  });

  // Local text state
  const [localTitle, setLocalTitle] = useState<string | null>(currentSlide?.text.title || null);
  const [localBody, setLocalBody] = useState<string>(currentSlide?.text.body || '');

  const hasTitle = !!(localTitle);

  // Render slide on style changes
  const { execute: renderSlide, isLoading: rendering } = useApiAction({
    action: () => api.applyTextToSlide(projectId, selectedSlide),
    onSuccess: (newSession) => updateProject(newSession),
    onError: (error) => setError(error)
  });

  // Debounced text save → render (sequential: save first, then render)
  const { schedule: scheduleTextSyncAndRender, flush: flushTextSync } = useDebouncedRender({
    projectId,
    slideIndex: selectedSlide,
    onSuccess: updateProject,
    onError: (error) => setError(error),
  });

  // Text change handler
  const handleTextChange = useCallback((which: 'title' | 'body', text: string) => {
    const newTitle = which === 'title' ? text : localTitle;
    const newBody = which === 'body' ? text : localBody;
    if (which === 'title') setLocalTitle(text);
    else setLocalBody(text);
    scheduleTextSyncAndRender(newTitle, newBody);
  }, [scheduleTextSyncAndRender, localTitle, localBody]);

  // applyToAll — defined before the mount effect so it can be listed as a dep
  const { execute: applyToAll, isLoading: applyingToAll } = useApiAction({
    action: async () => {
      if (!style) throw new Error('No style to apply');
      await api.applyStyleToAll(projectId, style);
      return await api.applyTextToAll(projectId);
    },
    onSuccess: (newSession) => updateProject(newSession),
    onError: (error) => setError(error)
  });

  // Update local text when selected slide changes.
  // Read via slidesRef so this only fires on slide navigation, not on every project update.
  useEffect(() => {
    const slide = slidesRef.current[selectedSlide];
    setLocalTitle(slide?.text.title || null);
    setLocalBody(slide?.text.body || '');
  }, [selectedSlide]);

  // If no title, auto-select body
  useEffect(() => {
    if (!hasTitle && selectedBox === 'title') {
      setSelectedBox('body');
    }
  }, [hasTitle, selectedBox]);

  // Auto-apply to all slides on first render.
  // applyToAll is stable (useCallback with [] deps) so this runs once on mount.
  useEffect(() => {
    if (slidesRef.current.length > 0 && slidesRef.current.some((s) => s.background_image_url && !s.final_image_url)) {
      applyToAll();
    }
  }, [applyToAll]);

  // Auto-render when style changes (fires when styleUpdating transitions true → false)
  const prevStyleUpdatingRef = useRef(false);
  useEffect(() => {
    const wasUpdating = prevStyleUpdatingRef.current;
    prevStyleUpdatingRef.current = styleUpdating;
    if (wasUpdating && !styleUpdating) {
      renderSlide();
    }
  }, [styleUpdating, renderSlide]);

  const handleBack = useCallback(async () => {
    await flushTextSync();
    onBack();
  }, [flushTextSync, onBack]);

  const handleSlideChange = useCallback(async (index: number) => {
    await flushTextSync();
    setSelectedSlide(index);
  }, [flushTextSync]);

  const { handleBoxMouseDown, handleResizeMouseDown } = useDragResize({
    containerRef,
    style,
    selectedBox,
    setSelectedBox,
    updateLocalStyle: updateStyle,
  });

  const handleExport = () => {
    window.open(api.getExportZipUrl(projectId), '_blank');
  };

  const hasFinalImages = slides.some((s) => s.final_image_url);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={handleBack}
            className="px-3 py-1.5 text-gray-600 dark:text-gray-300 hover:text-gray-800 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
          >
            &larr; Back
          </button>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Typography & Layout</h2>
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
