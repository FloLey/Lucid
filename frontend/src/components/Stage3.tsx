import type { Session } from '../types';
import * as api from '../services/api';

interface Stage3Props {
  sessionId: string;
  session: Session | null;
  loading: boolean;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  updateSession: (session: Session) => void;
  onNext: () => void;
  onBack: () => void;
}

export default function Stage3({
  sessionId,
  session,
  loading,
  setLoading,
  setError,
  updateSession,
  onNext,
  onBack,
}: Stage3Props) {
  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    try {
      const sess = await api.generateImages(sessionId);
      updateSession(sess);
    } catch (err) {
      setError('Failed to generate images');
    } finally {
      setLoading(false);
    }
  };

  const handleRegenerateImage = async (index: number) => {
    setLoading(true);
    try {
      const sess = await api.regenerateImage(sessionId, index);
      updateSession(sess);
    } catch (err) {
      setError('Failed to regenerate image');
    } finally {
      setLoading(false);
    }
  };

  const slides = session?.slides || [];
  const hasImages = slides.some((s) => s.image_data);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={onBack}
            className="px-3 py-1.5 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
          >
            ← Back
          </button>
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Background Images</h2>
            <p className="text-sm text-gray-500">
              Generate background images for your carousel slides
            </p>
          </div>
        </div>
        <div className="flex gap-3">
          <button
            onClick={handleGenerate}
            disabled={loading}
            className="px-4 py-2 bg-white border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
          >
            {loading ? 'Generating...' : hasImages ? 'Regenerate All' : 'Generate Images'}
          </button>
          {hasImages && (
            <button
              onClick={onNext}
              className="px-4 py-2 bg-lucid-600 text-white font-medium rounded-lg hover:bg-lucid-700 transition-colors"
            >
              Next: Apply Typography →
            </button>
          )}
        </div>
      </div>

      {/* Image Grid */}
      {!hasImages ? (
        <div className="bg-gray-50 rounded-xl border border-dashed border-gray-300 p-12 text-center">
          <p className="text-gray-500">
            Click "Generate Images" to create background images for each slide
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
          {slides.map((slide, index) => (
            <div
              key={index}
              className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden"
            >
              <div className="aspect-[4/5] relative bg-gray-100">
                {slide.image_data ? (
                  <img
                    src={`data:image/png;base64,${slide.image_data}`}
                    alt={`Slide ${index + 1}`}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-gray-400">
                    No image
                  </div>
                )}
              </div>
              <div className="p-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-gray-900">
                    Slide {index + 1}
                  </span>
                  <button
                    onClick={() => handleRegenerateImage(index)}
                    disabled={loading}
                    className="text-xs text-lucid-600 hover:text-lucid-700 disabled:opacity-50"
                  >
                    Regen
                  </button>
                </div>
                <p className="text-xs text-gray-500 truncate">
                  {slide.image_prompt || 'No prompt'}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Prompts Reference */}
      {hasImages && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="text-sm font-semibold text-gray-900 mb-3">Image Prompts</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {slides.map((slide, index) => (
              <div key={index} className="p-3 bg-gray-50 rounded-lg text-sm">
                <span className="font-medium text-lucid-600">{index + 1}.</span>{' '}
                <span className="text-gray-700">{slide.image_prompt || 'No prompt'}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
