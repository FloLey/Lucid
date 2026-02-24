import { useState, useEffect, useRef, useCallback } from 'react';
import * as api from '../services/api';
import { useProject } from '../contexts/ProjectContext';
import { useDragResize } from '../hooks/useDragResize';
import { useStyleManager } from '../hooks/useStyleManager';
import { useApiAction } from '../hooks/useApiAction';
import { useDebouncedRender } from '../hooks/useDebouncedRender';
import { useTemplateManager } from '../hooks/useTemplateManager';
import { getErrorMessage } from '../utils/error';
import CarouselCanvas from './CarouselCanvas';
import SlideThumbnails from './SlideThumbnails';
import StyleToolbar from './StyleToolbar';

type SelectedBox = 'title' | 'body';
type ExportFormat = 'png' | 'jpeg' | 'webp';


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

  // Export format selection (F5)
  const [exportFormat, setExportFormat] = useState<ExportFormat>('png');

  // Save-as-template state (F6)
  const {
    showTemplateForm,
    templateName,
    savingTemplate,
    templateSaved,
    setTemplateName,
    openForm: openTemplateForm,
    closeForm: closeTemplateForm,
    saveTemplate: handleSaveTemplate,
  } = useTemplateManager({
    projectConfig: project?.project_config,
    slideCount: project?.slide_count || 5,
    onError: (msg) => setError(msg),
  });

  const containerRef = useRef<HTMLDivElement>(null);

  const slides = project?.slides || [];
  const currentSlide = slides[selectedSlide];

  // Keep a ref to slides so effects can read the latest value without re-running
  const slidesRef = useRef(slides);
  slidesRef.current = slides;

  // Style management — now with undo/redo and replaceStyle (F1)
  const { style, updateStyle, replaceStyle, isUpdating: styleUpdating, undo, redo } = useStyleManager({
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

  // F3: handle slide reorder from thumbnail drag-and-drop
  const handleReorder = useCallback(async (newOrder: number[]) => {
    try {
      const updated = await api.reorderSlides(projectId, newOrder);
      updateProject(updated);
      // Keep the selected slide pointing to the same logical slide
      const currentIndex = newOrder.indexOf(selectedSlide);
      if (currentIndex !== -1) setSelectedSlide(currentIndex);
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to reorder slides'));
    }
  }, [projectId, selectedSlide, updateProject, setError]);

  const { handleBoxMouseDown, handleResizeMouseDown } = useDragResize({
    containerRef,
    style,
    selectedBox,
    setSelectedBox,
    updateLocalStyle: updateStyle,
  });

  // F5: export with selected format
  const handleExport = () => {
    window.open(api.getExportZipUrl(projectId, exportFormat), '_blank');
  };

  // F10: copy style from another slide
  const handleCopyStyleFrom = useCallback(async (sourceIndex: number) => {
    const sourceSlide = slidesRef.current[sourceIndex];
    if (!sourceSlide?.style) return;
    await replaceStyle(sourceSlide.style);
  }, [replaceStyle]);

  // F2 keyboard nav + F1 undo/redo shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      const inInput =
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable;

      // Undo / redo (always, regardless of input focus)
      if ((e.metaKey || e.ctrlKey) && e.key === 'z') {
        e.preventDefault();
        if (e.shiftKey) {
          redo();
        } else {
          undo();
        }
        return;
      }

      // Arrow key slide navigation (only when not typing in an input)
      if (!inInput) {
        if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
          e.preventDefault();
          handleSlideChange(Math.max(0, selectedSlide - 1));
        } else if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
          e.preventDefault();
          handleSlideChange(Math.min(slidesRef.current.length - 1, selectedSlide + 1));
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [selectedSlide, handleSlideChange, undo, redo]);

  const hasFinalImages = slides.some((s) => s.final_image_url);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
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
          <div className="flex items-center gap-2 flex-wrap">
            {/* F6: Save as Template */}
            {showTemplateForm ? (
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={templateName}
                  onChange={(e) => setTemplateName(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleSaveTemplate();
                    if (e.key === 'Escape') closeTemplateForm();
                  }}
                  placeholder="Template name"
                  className="text-sm border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded px-2 py-1.5 w-36 focus:outline-none focus:ring-2 focus:ring-lucid-500"
                  autoFocus
                />
                <button
                  onClick={handleSaveTemplate}
                  disabled={savingTemplate || !templateName.trim()}
                  className="px-2 py-1.5 text-sm bg-lucid-600 text-white rounded hover:bg-lucid-700 disabled:opacity-50 transition-colors"
                >
                  {savingTemplate ? 'Saving…' : 'Save'}
                </button>
                <button
                  onClick={closeTemplateForm}
                  className="px-2 py-1.5 text-sm bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                >
                  Cancel
                </button>
              </div>
            ) : templateSaved ? (
              <span className="text-sm text-green-600 dark:text-green-400">Template saved!</span>
            ) : (
              <button
                onClick={openTemplateForm}
                className="px-3 py-1.5 text-sm bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
              >
                Save as Template
              </button>
            )}

            {/* F5: Format selector + Export button */}
            <div className="flex items-center gap-1">
              <select
                value={exportFormat}
                onChange={(e) => setExportFormat(e.target.value as ExportFormat)}
                className="text-sm border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-lg px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-lucid-500"
                title="Export format"
              >
                <option value="png">PNG</option>
                <option value="jpeg">JPEG</option>
                <option value="webp">WebP</option>
              </select>
              <button
                onClick={handleExport}
                className="px-4 py-2 bg-lucid-600 text-white font-medium rounded-lg hover:bg-lucid-700 transition-colors"
              >
                Export ZIP
              </button>
            </div>
          </div>
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
          onUndo={undo}
          onRedo={redo}
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

      {/* Slide thumbnails with drag-and-drop reorder (F3) */}
      <SlideThumbnails
        slides={slides}
        selectedSlide={selectedSlide}
        onSlideChange={handleSlideChange}
        onReorder={handleReorder}
      />

      {/* F10: Copy style from another slide */}
      {slides.length > 1 && style && (
        <div className="flex items-center gap-2 text-sm">
          <span className="text-gray-500 dark:text-gray-400 text-xs">Copy style from:</span>
          <select
            defaultValue=""
            onChange={(e) => {
              if (e.target.value !== '') {
                handleCopyStyleFrom(Number(e.target.value));
                e.target.value = '';
              }
            }}
            className="text-xs border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-lucid-500"
          >
            <option value="">Select slide…</option>
            {slides.map((_, i) =>
              i !== selectedSlide ? (
                <option key={i} value={i}>
                  Slide {i + 1}
                </option>
              ) : null,
            )}
          </select>
        </div>
      )}
    </div>
  );
}
