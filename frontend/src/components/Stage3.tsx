import { useState, useEffect } from 'react';
import type { Session, AppConfig } from '../types';
import * as api from '../services/api';
import { getErrorMessage } from '../utils/error';

interface Stage3Props {
  sessionId: string;
  session: Session | null;
  stageLoading: boolean;
  setStageLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  updateSession: (session: Session) => void;
  onNext: () => void;
  onBack: () => void;
}

export default function Stage3({
  sessionId,
  session,
  stageLoading,
  setStageLoading,
  setError,
  updateSession,
  onNext,
  onBack,
}: Stage3Props) {
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [styleInstructions, setStyleInstructions] = useState('');

  // Load config defaults on mount
  useEffect(() => {
    const loadConfig = async () => {
      try {
        const configData = await api.getConfig();
        setConfig(configData);

        // Check if image prompts have been generated yet
        const hasImagePrompts = session?.slides?.some(slide => slide.image_prompt);

        if (!hasImagePrompts) {
          // New session - use config default instructions
          if (configData.stage_instructions.stage2) {
            setStyleInstructions(configData.stage_instructions.stage2);
          }
        } else {
          // Existing session - use session value
          setStyleInstructions(session?.image_style_instructions || '');
        }
      } catch (err) {
        console.error('Failed to load config:', err);
      }
    };
    loadConfig();
  }, [session]);
  const [editingPrompt, setEditingPrompt] = useState<number | null>(null);

  const handleGenerate = async () => {
    setStageLoading(true);
    setError(null);
    try {
      const sess = await api.generatePrompts(sessionId, styleInstructions || undefined);
      updateSession(sess);
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to generate image prompts'));
    } finally {
      setStageLoading(false);
    }
  };

  const handleRegeneratePrompt = async (index: number) => {
    setStageLoading(true);
    try {
      const sess = await api.regeneratePrompt(sessionId, index);
      updateSession(sess);
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to regenerate prompt'));
    } finally {
      setStageLoading(false);
    }
  };

  const handleUpdatePrompt = async (index: number, prompt: string) => {
    try {
      const sess = await api.updatePrompt(sessionId, index, prompt);
      updateSession(sess);
      setEditingPrompt(null);
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to update prompt'));
    }
  };

  const slides = session?.slides || [];
  const hasPrompts = slides.some((s) => s.image_prompt);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-full min-h-0">
      {/* Left Column - Slide Texts */}
      <div className="space-y-6 overflow-y-auto min-h-0">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Slide Texts</h2>

          <div className="space-y-3 max-h-64 overflow-y-auto">
            {slides.map((slide, index) => (
              <div
                key={index}
                className="p-3 bg-gray-50 rounded-lg text-sm"
              >
                <span className="font-medium text-lucid-600">
                  {index + 1}.
                </span>{' '}
                {slide.text.title && (
                  <span className="font-semibold">{slide.text.title}: </span>
                )}
                <span className="text-gray-700">{slide.text.body}</span>
              </div>
            ))}
          </div>

          <div className="mt-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Image Style Instructions
            </label>
            <textarea
              value={styleInstructions}
              onChange={(e) => setStyleInstructions(e.target.value)}
              placeholder="e.g., Modern, minimalist, warm colors, professional photography style"
              className="w-full h-24 px-4 py-3 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-lucid-500"
            />
          </div>

          <button
            onClick={handleGenerate}
            disabled={stageLoading || slides.length === 0}
            className="mt-4 w-full py-3 bg-lucid-600 text-white font-medium rounded-lg hover:bg-lucid-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {stageLoading ? 'Generating...' : hasPrompts ? 'Regenerate All Prompts' : 'Generate Image Prompts'}
          </button>
        </div>
      </div>

      {/* Right Column - Image Prompts */}
      <div className="flex flex-col min-h-0">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <button
              onClick={onBack}
              className="px-3 py-1.5 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
            >
              ← Back
            </button>
            <h2 className="text-lg font-semibold text-gray-900">Image Prompts</h2>
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
        {session?.shared_prompt_prefix && (
          <div className="p-3 bg-lucid-50 rounded-lg">
            <span className="text-xs font-medium text-lucid-700">Shared Style:</span>
            <p className="text-sm text-lucid-900">{session.shared_prompt_prefix}</p>
          </div>
        )}

        {!hasPrompts ? (
          <div className="bg-gray-50 rounded-xl border border-dashed border-gray-300 p-8 text-center">
            <p className="text-gray-500">
              Click "Generate Image Prompts" to create visual concepts for each slide
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {slides.map((slide, index) => (
              <div
                key={index}
                className="bg-white rounded-lg shadow-sm border border-gray-200 p-4"
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
                      disabled={stageLoading}
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
                  <p className="text-gray-700 text-sm">
                    {slide.image_prompt || 'No prompt generated'}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
        </div>
      </div>
    </div>
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
        className="w-full h-24 px-3 py-2 border border-gray-300 rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-lucid-500"
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
          className="px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
