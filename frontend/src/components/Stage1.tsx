import { useState, useEffect } from 'react';
import * as api from '../services/api';
import { getErrorMessage } from '../utils/error';
import { useProject } from '../contexts/ProjectContext';
import { SLIDE_COUNT_OPTIONS, LANGUAGES } from '../constants';
import Spinner from './Spinner';
import StageLayout from './StageLayout';

const WORDS_PER_SLIDE_OPTIONS = [
  { value: 'ai', label: 'Let AI decide' },
  { value: 'short', label: 'Short (20–50 words)' },
  { value: 'medium', label: 'Medium (50–100 words)' },
  { value: 'long', label: 'Long (100–200 words)' },
];

export default function Stage1() {
  const {
    projectId,
    currentProject: project,
    stageLoading: loading,
    setStageLoading: setLoading,
    setError,
    updateProject,
    advanceStage: onNext,
  } = useProject();

  const [draftText, setDraftText] = useState('');
  const [numSlides, setNumSlides] = useState<number | null>(null);
  const [includeTitles, setIncludeTitles] = useState(true);
  const [language, setLanguage] = useState('English');
  const [instructions, setInstructions] = useState('');
  const [wordsPerSlide, setWordsPerSlide] = useState<string>('ai');

  const isSingleSlide = (project?.slide_count ?? 0) === 1;

  // Apply project-scoped config defaults or existing session values
  useEffect(() => {
    if (!project) return;

    const cfg = project.project_config;
    const isNewProject = !project.slides || project.slides.length === 0;

    if (isNewProject) {
      setNumSlides(cfg?.global_defaults.num_slides ?? null);
      setIncludeTitles(cfg?.global_defaults.include_titles ?? true);
      setLanguage(cfg?.global_defaults.language ?? 'English');
      if (cfg?.stage_instructions.stage1) {
        setInstructions(cfg.stage_instructions.stage1);
      }
      if (project.draft_text) {
        setDraftText(project.draft_text);
      }
    } else {
      setDraftText(project.draft_text || '');
      setNumSlides(project.num_slides ?? cfg?.global_defaults.num_slides ?? null);
      setIncludeTitles(project.include_titles ?? cfg?.global_defaults.include_titles ?? true);
      setLanguage(project.language || cfg?.global_defaults.language || 'English');
      setInstructions(project.additional_instructions || '');
    }
  }, [project]);

  const [editingSlide, setEditingSlide] = useState<number | null>(null);
  const [regeneratingSlides, setRegeneratingSlides] = useState<Set<number>>(new Set());
  const [regenInstructionSlide, setRegenInstructionSlide] = useState<number | null>(null);
  const [regenInstruction, setRegenInstruction] = useState('');

  const handleGenerate = async () => {
    if (!draftText.trim()) {
      setError('Please enter a draft text');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const sess = await api.generateSlideTexts(
        projectId,
        draftText,
        wordsPerSlide === 'keep_as_is' ? undefined : (numSlides ?? undefined),
        includeTitles,
        instructions || undefined,
        language,
        wordsPerSlide === 'ai' ? undefined : wordsPerSlide
      );
      updateProject(sess);
      // Re-fetch after a delay so the background title-generation task can finish
      if (sess.name.startsWith('Untitled')) {
        setTimeout(async () => {
          try {
            const refreshed = await api.getProject(projectId);
            updateProject(refreshed);
          } catch (err) {
            console.error('Failed to re-fetch project for title update:', err);
          }
        }, 3000);
      }
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to generate slide texts'));
    } finally {
      setLoading(false);
    }
  };

  const handleRegenerateSlide = async (index: number, instruction?: string) => {
    setRegenInstructionSlide(null);
    setRegenInstruction('');
    setRegeneratingSlides((prev) => new Set(prev).add(index));
    try {
      const sess = await api.regenerateSlideText(projectId, index, instruction || undefined);
      updateProject(sess);
    } catch (err) {
      setError(getErrorMessage(err, `Failed to regenerate slide ${index + 1}`));
    } finally {
      setRegeneratingSlides((prev) => {
        const next = new Set(prev);
        next.delete(index);
        return next;
      });
    }
  };

  const handleUpdateSlide = async (index: number, title?: string, body?: string) => {
    try {
      const sess = await api.updateSlideText(projectId, index, title, body);
      updateProject(sess);
      setEditingSlide(null);
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to update slide'));
    }
  };

  const slides = project?.slides || [];
  const hasSlides = slides.length > 0;
  const isKeepAsIs = wordsPerSlide === 'keep_as_is';

  const generateButtonLabel = () => {
    if (loading) return isKeepAsIs ? 'Applying...' : 'Generating...';
    if (isKeepAsIs) return hasSlides ? 'Apply Draft as Slide' : 'Use Draft as Slide';
    return hasSlides ? 'Regenerate All' : 'Generate Slides';
  };

  return (
    <StageLayout
      leftPanel={
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Your Draft</h2>

          <textarea
            value={draftText}
            onChange={(e) => setDraftText(e.target.value)}
            placeholder="Paste your rough draft here... It can be messy, unstructured notes about what you want to share in your carousel."
            className="w-full h-48 px-4 py-3 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-lucid-500 focus:border-transparent"
          />

          {/* Words per slide */}
          <div className="mt-4">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Text length per slide
            </label>
            <select
              value={wordsPerSlide}
              onChange={(e) => setWordsPerSlide(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-lg focus:outline-none focus:ring-2 focus:ring-lucid-500"
            >
              {WORDS_PER_SLIDE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
              {isSingleSlide && (
                <option value="keep_as_is">Keep as is (use draft text directly)</option>
              )}
            </select>
          </div>

          {/* Slides / Language / Titles — hidden when keep_as_is */}
          {!isKeepAsIs && (
            <div className="mt-4 grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Number of Slides
                </label>
                <select
                  value={numSlides ?? 'auto'}
                  onChange={(e) => setNumSlides(e.target.value === 'auto' ? null : Number(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-lg focus:outline-none focus:ring-2 focus:ring-lucid-500"
                >
                  <option value="auto">Let AI decide</option>
                  {SLIDE_COUNT_OPTIONS.map((n) => (
                    <option key={n} value={n}>{n} slides</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Language
                </label>
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-lg focus:outline-none focus:ring-2 focus:ring-lucid-500"
                >
                  {LANGUAGES.map((lang) => (
                    <option key={lang} value={lang}>{lang}</option>
                  ))}
                </select>
              </div>

              <div className="flex items-center">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={includeTitles}
                    onChange={(e) => setIncludeTitles(e.target.checked)}
                    className="w-4 h-4 text-lucid-600 rounded focus:ring-lucid-500"
                  />
                  <span className="text-sm font-medium text-gray-700">Include titles</span>
                </label>
              </div>
            </div>
          )}

          {!isKeepAsIs && (
            <div className="mt-4">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Additional Instructions (optional)
              </label>
              <input
                type="text"
                value={instructions}
                onChange={(e) => setInstructions(e.target.value)}
                placeholder="e.g., Make it conversational, target entrepreneurs"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-lg focus:outline-none focus:ring-2 focus:ring-lucid-500"
              />
            </div>
          )}

          <button
            onClick={handleGenerate}
            disabled={loading || !draftText.trim()}
            className="mt-6 w-full py-3 bg-lucid-600 text-white font-medium rounded-lg hover:bg-lucid-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {generateButtonLabel()}
          </button>
        </div>
      }
      rightPanel={
        <>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Slide Texts</h2>
            {hasSlides && !loading && regeneratingSlides.size === 0 && (
              <button
                onClick={onNext}
                className="px-4 py-2 bg-lucid-600 text-white font-medium rounded-lg hover:bg-lucid-700 transition-colors"
              >
                Next: Choose Style &rarr;
              </button>
            )}
          </div>

          <div className="overflow-y-auto flex-1 min-h-0 space-y-4 pr-1">
            {loading && regeneratingSlides.size === 0 ? (
              Array.from({ length: isKeepAsIs ? 1 : (numSlides ?? 3) }).map((_, index) => (
                <div key={index} className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4">
                  <span className="text-sm font-medium text-lucid-600">Slide {index + 1}</span>
                  <div className="flex items-center gap-3 mt-3 text-gray-400">
                    <Spinner size="sm" />
                    <span className="text-sm">Generating...</span>
                  </div>
                </div>
              ))
            ) : !hasSlides ? (
              <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl border border-dashed border-gray-300 dark:border-gray-600 p-8 text-center">
                <p className="text-gray-500 dark:text-gray-400">
                  Enter your draft and click "{isSingleSlide ? 'Use Draft as Slide' : 'Generate Slides'}" to create slide texts
                </p>
              </div>
            ) : (
              slides.map((slide, index) => (
                <div key={index} className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4">
                  <div className="flex items-start justify-between mb-2">
                    <span className="text-sm font-medium text-lucid-600">Slide {index + 1}</span>
                    <div className="flex gap-2">
                      <button
                        onClick={() => setEditingSlide(editingSlide === index ? null : index)}
                        className="text-xs text-gray-500 hover:text-gray-700"
                        disabled={regeneratingSlides.has(index)}
                      >
                        {editingSlide === index ? 'Cancel' : 'Edit'}
                      </button>
                      <button
                        onClick={() => {
                          if (regenInstructionSlide === index) {
                            setRegenInstructionSlide(null);
                            setRegenInstruction('');
                          } else {
                            setRegenInstructionSlide(index);
                            setRegenInstruction('');
                          }
                        }}
                        disabled={regeneratingSlides.has(index)}
                        className="text-xs text-lucid-600 hover:text-lucid-700"
                      >
                        Regenerate
                      </button>
                    </div>
                  </div>

                  {regenInstructionSlide === index && !regeneratingSlides.has(index) && (
                    <div className="mb-2 flex gap-2">
                      <input
                        type="text"
                        value={regenInstruction}
                        onChange={(e) => setRegenInstruction(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') handleRegenerateSlide(index, regenInstruction);
                          if (e.key === 'Escape') { setRegenInstructionSlide(null); setRegenInstruction(''); }
                        }}
                        placeholder="Instruction (optional), Enter to regenerate"
                        className="flex-1 px-2 py-1 text-xs border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-lucid-500"
                        autoFocus
                      />
                      <button
                        onClick={() => handleRegenerateSlide(index, regenInstruction)}
                        className="px-2 py-1 text-xs bg-lucid-600 text-white rounded-lg hover:bg-lucid-700"
                      >
                        Go
                      </button>
                    </div>
                  )}

                  {regeneratingSlides.has(index) ? (
                    <div className="flex items-center gap-3 text-gray-400">
                      <Spinner size="sm" />
                      <span className="text-sm">Regenerating...</span>
                    </div>
                  ) : editingSlide === index ? (
                    <SlideEditor
                      slide={slide}
                      includeTitles={includeTitles}
                      onSave={(title, body) => handleUpdateSlide(index, title, body)}
                      onCancel={() => setEditingSlide(null)}
                    />
                  ) : (
                    <>
                      {slide.text.title && (
                        <h3 className="font-semibold text-gray-900 dark:text-white mb-1">{slide.text.title}</h3>
                      )}
                      <p className="text-gray-700 dark:text-gray-300 text-sm">{slide.text.body}</p>
                    </>
                  )}
                </div>
              ))
            )}
          </div>
        </>
      }
    />
  );
}

interface SlideEditorProps {
  slide: { text: { title: string | null; body: string } };
  includeTitles: boolean;
  onSave: (title?: string, body?: string) => void;
  onCancel: () => void;
}

function SlideEditor({ slide, includeTitles, onSave, onCancel }: SlideEditorProps) {
  const [title, setTitle] = useState(slide.text.title || '');
  const [body, setBody] = useState(slide.text.body);

  return (
    <div className="space-y-3">
      {includeTitles && (
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Title"
          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-lucid-500"
        />
      )}
      <textarea
        value={body}
        onChange={(e) => setBody(e.target.value)}
        placeholder="Body text"
        className="w-full h-24 px-3 py-2 border border-gray-300 rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-lucid-500"
      />
      <div className="flex gap-2">
        <button
          onClick={() => onSave(includeTitles ? title : undefined, body)}
          className="px-3 py-1.5 text-sm bg-lucid-600 text-white rounded-lg hover:bg-lucid-700"
        >
          Save
        </button>
        <button
          onClick={onCancel}
          className="px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
