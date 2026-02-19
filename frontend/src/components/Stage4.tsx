import { useState } from 'react';
import * as api from '../services/api';
import { getErrorMessage } from '../utils/error';
import { useProject } from '../contexts/ProjectContext';
import Spinner from './Spinner';
import StageLayout from './StageLayout';

export default function Stage4() {
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

  const [regeneratingImages, setRegeneratingImages] = useState<Set<number>>(new Set());

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    try {
      const sess = await api.generateImages(projectId);
      updateProject(sess);
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to generate images'));
    } finally {
      setLoading(false);
    }
  };

  const handleRegenerateImage = async (index: number) => {
    setRegeneratingImages((prev) => new Set(prev).add(index));
    try {
      const sess = await api.regenerateImage(projectId, index);
      updateProject(sess);
    } catch (err) {
      setError(getErrorMessage(err, `Failed to regenerate image ${index + 1}`));
    } finally {
      setRegeneratingImages((prev) => {
        const next = new Set(prev);
        next.delete(index);
        return next;
      });
    }
  };

  const slides = project?.slides || [];
  const hasImages = slides.some((s) => s.image_data);

  return (
    <StageLayout
      leftPanel={
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 flex flex-col min-h-0">
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
          </div>

          {project?.shared_prompt_prefix && (
            <div className="p-3 bg-lucid-50 rounded-lg mb-2">
              <span className="text-xs font-medium text-lucid-700">Shared Style:</span>
              <p className="text-sm text-lucid-900">{project?.shared_prompt_prefix}</p>
            </div>
          )}

          <div className="overflow-y-auto flex-1 min-h-0 space-y-3">
            {slides.map((slide, index) => (
              <div key={index} className="p-3 bg-gray-50 rounded-lg text-sm">
                <span className="font-medium text-lucid-600">Slide {index + 1}</span>
                <p className="text-gray-500 text-xs mt-1">
                  {slide.image_prompt || 'No prompt generated'}
                </p>
              </div>
            ))}
          </div>

          <button
            onClick={handleGenerate}
            disabled={loading || slides.length === 0}
            className="mt-4 w-full py-3 bg-lucid-600 text-white font-medium rounded-lg hover:bg-lucid-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Generating...' : hasImages ? 'Regenerate All Images' : 'Generate Images'}
          </button>
        </div>
      }
      rightPanel={
        <>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Background Images</h2>
            {hasImages && !loading && regeneratingImages.size === 0 && (
              <button
                onClick={onNext}
                className="px-4 py-2 bg-lucid-600 text-white font-medium rounded-lg hover:bg-lucid-700 transition-colors"
              >
                Next: Apply Typography →
              </button>
            )}
          </div>

          <div className="overflow-y-auto flex-1 min-h-0 space-y-4">
            {loading && regeneratingImages.size === 0 ? (
              slides.map((_, index) => (
                <div
                  key={index}
                  className="bg-white rounded-lg shadow-sm border border-gray-200 p-4"
                >
                  <span className="text-sm font-medium text-lucid-600">Slide {index + 1}</span>
                  <div className="flex items-center gap-3 mt-3 text-gray-400">
                    <Spinner size="sm" />
                    <span className="text-sm">Generating image...</span>
                  </div>
                </div>
              ))
            ) : !hasImages ? (
              <div className="bg-gray-50 rounded-xl border border-dashed border-gray-300 p-8 text-center">
                <p className="text-gray-500">
                  Click "Generate Images" to create background images for each slide
                </p>
              </div>
            ) : (
              slides.map((slide, index) => (
                <div
                  key={index}
                  className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden"
                >
                  <div className="flex items-start gap-4 p-4">
                    <div className="w-48 shrink-0 aspect-[4/5] relative bg-gray-100 rounded-lg overflow-hidden">
                      {regeneratingImages.has(index) ? (
                        <div className="w-full h-full flex items-center justify-center text-gray-400">
                          <Spinner size="md" />
                        </div>
                      ) : slide.image_data ? (
                        <img
                          src={`data:image/png;base64,${slide.image_data}`}
                          alt={`Slide ${index + 1}`}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-gray-400 text-xs">
                          No image
                        </div>
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium text-gray-900">Slide {index + 1}</span>
                        <button
                          onClick={() => handleRegenerateImage(index)}
                          disabled={regeneratingImages.has(index)}
                          className="text-xs text-lucid-600 hover:text-lucid-700 disabled:opacity-50"
                        >
                          Regen
                        </button>
                      </div>
                      {slide.text.title && (
                        <h3 className="font-semibold text-gray-900 text-sm mb-1">{slide.text.title}</h3>
                      )}
                      <p className="text-xs text-gray-700">{slide.text.body}</p>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </>
      }
    />
  );
}
