import { useState, useEffect } from 'react';
import * as api from '../services/api';
import { getErrorMessage } from '../utils/error';
import { useProject } from '../contexts/ProjectContext';
import { useAppConfig } from '../hooks/useAppConfig';
import Spinner from './Spinner';
import StageLayout from './StageLayout';

export default function Stage3() {
  const {
    projectId,
    currentProject: project,
    stageLoading: loading,
    setStageLoading: setLoading,
    setError,
    updateProject,
    advanceStage: onNext,
    previousStage: onBack,
  } = useProject();

  const config = useAppConfig();
  const [styleInstructions, setStyleInstructions] = useState('');

  // Sync style instructions when config or session changes
  useEffect(() => {
    if (!config) return;

    // Check if image prompts have been generated yet
    const hasImagePrompts = project?.slides?.some(slide => slide.image_prompt);

    if (!hasImagePrompts) {
      // New session - use config default instructions
      if (config.stage_instructions.stage2) {
        setStyleInstructions(config.stage_instructions.stage2);
      }
    } else {
      // Existing session - use session value
      setStyleInstructions(project?.image_style_instructions || '');
    }
  }, [config, project]);
  const [editingPrompt, setEditingPrompt] = useState<number | null>(null);

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    try {
      const sess = await api.generatePrompts(projectId, styleInstructions || undefined);
      updateProject(sess);
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to generate image prompts'));
    } finally {
      setLoading(false);
    }
  };

  const handleRegeneratePrompt = async (index: number) => {
    setLoading(true);
    try {
      const sess = await api.regeneratePrompt(projectId, index);
      updateProject(sess);
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to regenerate prompt'));
    } finally {
      setLoading(false);
    }
  };

  const handleUpdatePrompt = async (index: number, prompt: string) => {
    try {
      const sess = await api.updatePrompt(projectId, index, prompt);
      updateProject(sess);
      setEditingPrompt(null);
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to update prompt'));
    }
  };

  const slides = project?.slides || [];
  const hasPrompts = slides.some((s) => s.image_prompt);

  return (
    <StageLayout
      leftPanel={
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Slide Texts</h2>

          <div className="space-y-3 max-h-64 overflow-y-auto">
            {slides.map((slide, index) => (
              <div
                key={index}
                className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg text-sm"
              >
                <span className="font-medium text-lucid-600">
                  {index + 1}.
                </span>{' '}
                {slide.text.title && (
                  <span className="font-semibold dark:text-gray-200">{slide.text.title}: </span>
                )}
                <span className="text-gray-700 dark:text-gray-300">{slide.text.body}</span>
              </div>
            ))}
          </div>

          <div className="mt-6">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Image Style Instructions
            </label>
            <textarea
              value={styleInstructions}
              onChange={(e) => setStyleInstructions(e.target.value)}
              placeholder="e.g., Modern, minimalist, warm colors, professional photography style"
              className="w-full h-24 px-4 py-3 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-lucid-500"
            />
          </div>

          <button
            onClick={handleGenerate}
            disabled={loading || slides.length === 0}
            className="mt-4 w-full py-3 bg-lucid-600 text-white font-medium rounded-lg hover:bg-lucid-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Spinner size="sm" />
                Generating...
              </>
            ) : hasPrompts ? 'Regenerate All Prompts' : 'Generate Image Prompts'}
          </button>
        </div>
      }
      rightPanel={
        <>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <button
                onClick={onBack}
                className="px-3 py-1.5 text-gray-600 dark:text-gray-300 hover:text-gray-800 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
              >
                ← Back
              </button>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Image Prompts</h2>
            </div>
            {hasPrompts && (
              <button
                onClick={onNext}
                className="px-4 py-2 bg-lucid-600 text-white font-medium rounded-lg hover:bg-lucid-700 transition-colors"
              >
                Next: Generate Images →
              </button>
            )}
          </div>

          <div className="overflow-y-auto flex-1 min-h-0 space-y-4">
          {project?.shared_prompt_prefix && (
            <div className="p-3 bg-lucid-50 rounded-lg">
              <span className="text-xs font-medium text-lucid-700">Shared Style:</span>
              <p className="text-sm text-lucid-900">{project?.shared_prompt_prefix}</p>
            </div>
          )}

          {!hasPrompts ? (
            <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl border border-dashed border-gray-300 dark:border-gray-600 p-8 text-center">
              <p className="text-gray-500 dark:text-gray-400">
                Click "Generate Image Prompts" to create visual concepts for each slide
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {slides.map((slide, index) => (
                <div
                  key={index}
                  className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4"
                >
                  <div className="flex items-start justify-between mb-2">
                    <span className="text-sm font-medium text-lucid-600">
                      Slide {index + 1}
                    </span>
                    <div className="flex gap-2">
                      <button
                        onClick={() => setEditingPrompt(editingPrompt === index ? null : index)}
                        className="text-xs text-gray-500 hover:text-gray-700"
                      >
                        {editingPrompt === index ? 'Cancel' : 'Edit'}
                      </button>
                      <button
                        onClick={() => handleRegeneratePrompt(index)}
                        disabled={loading}
                        className="text-xs text-lucid-600 hover:text-lucid-700"
                      >
                        Regenerate
                      </button>
                    </div>
                  </div>

                  {editingPrompt === index ? (
                    <PromptEditor
                      prompt={slide.image_prompt || ''}
                      onSave={(prompt) => handleUpdatePrompt(index, prompt)}
                      onCancel={() => setEditingPrompt(null)}
                    />
                  ) : (
                    <p className="text-gray-700 dark:text-gray-300 text-sm">
                      {slide.image_prompt || 'No prompt generated'}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
          </div>
        </>
      }
    />
  );
}

interface PromptEditorProps {
  prompt: string;
  onSave: (prompt: string) => void;
  onCancel: () => void;
}

function PromptEditor({ prompt, onSave, onCancel }: PromptEditorProps) {
  const [value, setValue] = useState(prompt);

  return (
    <div className="space-y-3">
      <textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Image prompt"
        className="w-full h-24 px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-lucid-500"
      />
      <div className="flex gap-2">
        <button
          onClick={() => onSave(value)}
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
