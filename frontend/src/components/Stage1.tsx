import { useState } from 'react';
import type { Session } from '../types';
import * as api from '../services/api';
import { getErrorMessage } from '../utils/error';

interface Stage1Props {
  sessionId: string;
  session: Session | null;
  loading: boolean;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  updateSession: (session: Session) => void;
  onNext: () => void;
  onBack: () => void;
}

export default function Stage1({
  sessionId,
  session,
  loading,
  setLoading,
  setError,
  updateSession,
  onNext,
}: Stage1Props) {
  const [draftText, setDraftText] = useState(session?.draft_text || '');
  const [numSlides, setNumSlides] = useState(session?.num_slides || 5);
  const [includeTitles, setIncludeTitles] = useState(session?.include_titles ?? true);
  const [language, setLanguage] = useState(session?.language || 'English');
  const [instructions, setInstructions] = useState(session?.additional_instructions || '');
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
        sessionId,
        draftText,
        numSlides,
        includeTitles,
        instructions || undefined,
        language
      );
      updateSession(sess);
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
      const sess = await api.regenerateSlideText(sessionId, index, instruction || undefined);
      updateSession(sess);
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
      const sess = await api.updateSlideText(sessionId, index, title, body);
      updateSession(sess);
      setEditingSlide(null);
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to update slide'));
    }
  };

  const slides = session?.slides || [];
  const hasSlides = slides.length > 0;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-full min-h-0">
      {/* Left Column - Inputs */}
      <div className="space-y-6 overflow-y-auto min-h-0">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Your Draft</h2>

          <textarea
            value={draftText}
            onChange={(e) => setDraftText(e.target.value)}
            placeholder="Paste your rough draft here... It can be messy, unstructured notes about what you want to share in your carousel."
            className="w-full h-48 px-4 py-3 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-lucid-500 focus:border-transparent"
          />

          <div className="mt-4 grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Number of Slides
              </label>
              <select
                value={numSlides}
                onChange={(e) => setNumSlides(Number(e.target.value))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-lucid-500"
              >
                {[3, 4, 5, 6, 7, 8, 9, 10].map((n) => (
                  <option key={n} value={n}>
                    {n} slides
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Language
              </label>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-lucid-500"
              >
                {['English', 'French', 'Spanish', 'German', 'Portuguese', 'Italian', 'Dutch', 'Arabic', 'Chinese', 'Japanese', 'Korean'].map((lang) => (
                  <option key={lang} value={lang}>
                    {lang}
                  </option>
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

          <div className="mt-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Additional Instructions (optional)
            </label>
            <input
              type="text"
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
              placeholder="e.g., Make it conversational, target entrepreneurs"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-lucid-500"
            />
          </div>

          <button
            onClick={handleGenerate}
            disabled={loading || !draftText.trim()}
            className="mt-6 w-full py-3 bg-lucid-600 text-white font-medium rounded-lg hover:bg-lucid-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Generating...' : hasSlides ? 'Regenerate All' : 'Generate Slides'}
          </button>
        </div>
      </div>

      {/* Right Column - Generated Slides */}
      <div className="flex flex-col min-h-0">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Slide Texts</h2>
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
            // Generating all slides — show spinner placeholders
            Array.from({ length: numSlides }).map((_, index) => (
              <div
                key={index}
                className="bg-white rounded-lg shadow-sm border border-gray-200 p-4"
              >
                <span className="text-sm font-medium text-lucid-600">Slide {index + 1}</span>
                <div className="flex items-center gap-3 mt-3 text-gray-400">
                  <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  <span className="text-sm">Generating...</span>
                </div>
              </div>
            ))
          ) : !hasSlides ? (
            <div className="bg-gray-50 rounded-xl border border-dashed border-gray-300 p-8 text-center">
              <p className="text-gray-500">
                Enter your draft and click "Generate Slides" to create slide texts
              </p>
            </div>
          ) : (
            slides.map((slide, index) => (
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
                    <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
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
                      <h3 className="font-semibold text-gray-900 mb-1">
                        {slide.text.title}
                      </h3>
                    )}
                    <p className="text-gray-700 text-sm">{slide.text.body}</p>
                  </>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
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
          className="px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
