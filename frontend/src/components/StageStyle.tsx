import { useState } from 'react';
import type { Session } from '../types';
import * as api from '../services/api';
import { getErrorMessage } from '../utils/error';

interface StageStyleProps {
  sessionId: string;
  session: Session | null;
  loading: boolean;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  updateSession: (session: Session) => void;
  onNext: () => void;
  onBack: () => void;
}

export default function StageStyle({
  sessionId,
  session,
  loading,
  setLoading,
  setError,
  updateSession,
  onNext,
  onBack,
}: StageStyleProps) {
  const [numProposals, setNumProposals] = useState(3);
  const [instructions, setInstructions] = useState('');

  const proposals = session?.style_proposals || [];
  const selectedIndex = session?.selected_style_proposal_index ?? null;
  const hasProposals = proposals.length > 0;

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    try {
      const sess = await api.generateStyleProposals(
        sessionId,
        numProposals,
        instructions || undefined
      );
      updateSession(sess);
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to generate style proposals'));
    } finally {
      setLoading(false);
    }
  };

  const handleSelect = async (index: number) => {
    try {
      const sess = await api.selectStyleProposal(sessionId, index);
      updateSession(sess);
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to select style proposal'));
    }
  };

  const slides = session?.slides || [];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-full min-h-0">
      {/* Left Column - Inputs */}
      <div className="space-y-6 overflow-y-auto min-h-0">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Slide Texts</h2>

          <div className="space-y-3 max-h-48 overflow-y-auto">
            {slides.map((slide, index) => (
              <div key={index} className="p-3 bg-gray-50 rounded-lg text-sm">
                <span className="font-medium text-lucid-600">{index + 1}.</span>{' '}
                {slide.text.title && (
                  <span className="font-semibold">{slide.text.title}: </span>
                )}
                <span className="text-gray-700">{slide.text.body}</span>
              </div>
            ))}
          </div>

          <div className="mt-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Number of Proposals
            </label>
            <div className="flex gap-2">
              {[1, 2, 3, 4, 5].map((n) => (
                <button
                  key={n}
                  onClick={() => setNumProposals(n)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    numProposals === n
                      ? 'bg-lucid-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {n}
                </button>
              ))}
            </div>
          </div>

          <div className="mt-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Additional Instructions (optional)
            </label>
            <textarea
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
              placeholder="e.g., Warm colors, minimalist, professional photography"
              className="w-full h-24 px-4 py-3 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-lucid-500 focus:border-transparent"
            />
          </div>

          <button
            onClick={handleGenerate}
            disabled={loading || slides.length === 0}
            className="mt-6 w-full py-3 bg-lucid-600 text-white font-medium rounded-lg hover:bg-lucid-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Generating...' : hasProposals ? 'Regenerate Proposals' : 'Generate Style Proposals'}
          </button>
        </div>
      </div>

      {/* Right Column - Proposals */}
      <div className="flex flex-col min-h-0">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <button
              onClick={onBack}
              className="px-3 py-1.5 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
            >
              &larr; Back
            </button>
            <h2 className="text-lg font-semibold text-gray-900">Style Proposals</h2>
          </div>
          {selectedIndex !== null && (
            <button
              onClick={onNext}
              className="px-4 py-2 bg-lucid-600 text-white font-medium rounded-lg hover:bg-lucid-700 transition-colors"
            >
              Next: Image Prompts &rarr;
            </button>
          )}
        </div>

        <div className="overflow-y-auto flex-1 min-h-0 space-y-4 pr-1">
          {loading ? (
            // Skeleton cards while generating
            Array.from({ length: numProposals }).map((_, index) => (
              <div
                key={index}
                className="bg-white rounded-lg shadow-sm border border-gray-200 p-4"
              >
                <span className="text-sm font-medium text-lucid-600">Proposal {index + 1}</span>
                <div className="mt-3 animate-pulse">
                  <div className="bg-gray-200 rounded-lg w-full mb-3" style={{ aspectRatio: '4/5' }} />
                  <div className="bg-gray-200 rounded h-4 w-3/4 mb-2" />
                  <div className="bg-gray-200 rounded h-4 w-1/2" />
                </div>
              </div>
            ))
          ) : !hasProposals ? (
            <div className="bg-gray-50 rounded-xl border border-dashed border-gray-300 p-8 text-center">
              <p className="text-gray-500">
                Click "Generate Style Proposals" to create visual style options for your carousel
              </p>
            </div>
          ) : (
            proposals.map((proposal) => (
              <button
                key={proposal.index}
                onClick={() => handleSelect(proposal.index)}
                className={`w-full text-left bg-white rounded-lg shadow-sm border-2 p-4 transition-colors ${
                  selectedIndex === proposal.index
                    ? 'border-lucid-500 ring-2 ring-lucid-200'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="flex items-start justify-between mb-2">
                  <span className="text-sm font-medium text-lucid-600">
                    Proposal {proposal.index + 1}
                  </span>
                  {selectedIndex === proposal.index && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-lucid-100 text-lucid-700">
                      Selected
                    </span>
                  )}
                </div>

                {proposal.preview_image && (
                  <img
                    src={`data:image/png;base64,${proposal.preview_image}`}
                    alt={`Style proposal ${proposal.index + 1}`}
                    className="w-full rounded-lg mb-3"
                    style={{ aspectRatio: '4/5' }}
                  />
                )}

                <p className="text-gray-700 text-sm">{proposal.description}</p>
              </button>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
