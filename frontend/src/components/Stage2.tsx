import { useState, useEffect } from 'react';
import * as api from '../services/api';
import { getErrorMessage } from '../utils/error';
import { useProject } from '../contexts/ProjectContext';
import { PROPOSAL_COUNT_OPTIONS } from '../constants';
import { StyleProposal } from '../types';
import Spinner from './Spinner';
import StageLayout from './StageLayout';

export default function Stage2() {
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

  const [numProposals, setNumProposals] = useState(3);
  const [instructions, setInstructions] = useState('');

  // Apply project-scoped config default instructions for new projects (no proposals yet)
  useEffect(() => {
    if (!project) return;
    const cfg = project.project_config;
    const isNewProject = !project.style_proposals || project.style_proposals.length === 0;
    if (isNewProject && cfg?.stage_instructions.stage_style) {
      setInstructions(cfg.stage_instructions.stage_style);
    }
  }, [project]);

  const proposals = project?.style_proposals || [];
  const selectedIndex = project?.selected_style_proposal_index ?? null;
  const hasProposals = proposals.length > 0;

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    try {
      const sess = await api.generateStyleProposals(
        projectId,
        numProposals,
        instructions || undefined
      );
      updateProject(sess);
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to generate style proposals'));
    } finally {
      setLoading(false);
    }
  };

  const handleSelect = async (index: number) => {
    try {
      const sess = await api.selectStyleProposal(projectId, index);
      updateProject(sess);
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to select style proposal'));
    }
  };

  const slides = project?.slides || [];

  return (
    <StageLayout
      leftPanel={
        <StyleControlPanel
          slides={slides}
          numProposals={numProposals}
          onNumProposalsChange={setNumProposals}
          instructions={instructions}
          onInstructionsChange={setInstructions}
          loading={loading}
          hasProposals={hasProposals}
          onGenerate={handleGenerate}
        />
      }
      rightPanel={
        <StyleProposalList
          loading={loading}
          numProposals={numProposals}
          hasProposals={hasProposals}
          proposals={proposals}
          selectedIndex={selectedIndex}
          onSelect={handleSelect}
          onBack={onBack}
          onNext={onNext}
        />
      }
    />
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

interface StyleControlPanelProps {
  slides: { text: { title: string | null; body: string } }[];
  numProposals: number;
  onNumProposalsChange: (n: number) => void;
  instructions: string;
  onInstructionsChange: (v: string) => void;
  loading: boolean;
  hasProposals: boolean;
  onGenerate: () => void;
}

function StyleControlPanel({
  slides,
  numProposals,
  onNumProposalsChange,
  instructions,
  onInstructionsChange,
  loading,
  hasProposals,
  onGenerate,
}: StyleControlPanelProps) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
      <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Slide Texts</h2>

      <div className="space-y-3 max-h-48 overflow-y-auto">
        {slides.map((slide, index) => (
          <div key={index} className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg text-sm">
            <span className="font-medium text-lucid-600">{index + 1}.</span>{' '}
            {slide.text.title && (
              <span className="font-semibold dark:text-gray-200">{slide.text.title}: </span>
            )}
            <span className="text-gray-700 dark:text-gray-300">{slide.text.body}</span>
          </div>
        ))}
      </div>

      <div className="mt-6">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Number of Proposals
        </label>
        <div className="flex gap-2">
          {PROPOSAL_COUNT_OPTIONS.map((n) => (
            <button
              key={n}
              onClick={() => onNumProposalsChange(n)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                numProposals === n
                  ? 'bg-lucid-600 text-white'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
              }`}
            >
              {n}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-4">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Additional Instructions (optional)
        </label>
        <textarea
          value={instructions}
          onChange={(e) => onInstructionsChange(e.target.value)}
          placeholder="e.g., Warm colors, minimalist, professional photography"
          className="w-full h-24 px-4 py-3 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-lucid-500 focus:border-transparent"
        />
      </div>

      <button
        onClick={onGenerate}
        disabled={loading || slides.length === 0}
        className="mt-6 w-full py-3 bg-lucid-600 text-white font-medium rounded-lg hover:bg-lucid-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
      >
        {loading ? (
          <>
            <Spinner size="sm" />
            Generating...
          </>
        ) : hasProposals ? 'Regenerate Proposals' : 'Generate Style Proposals'}
      </button>
    </div>
  );
}

interface StyleProposalListProps {
  loading: boolean;
  numProposals: number;
  hasProposals: boolean;
  proposals: StyleProposal[];
  selectedIndex: number | null;
  onSelect: (index: number) => void;
  onBack: () => void;
  onNext: () => void;
}

function StyleProposalList({
  loading,
  numProposals,
  hasProposals,
  proposals,
  selectedIndex,
  onSelect,
  onBack,
  onNext,
}: StyleProposalListProps) {
  return (
    <>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <button
            onClick={onBack}
            className="px-3 py-1.5 text-gray-600 dark:text-gray-300 hover:text-gray-800 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
          >
            &larr; Back
          </button>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Style Proposals</h2>
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
          Array.from({ length: numProposals }).map((_, index) => (
            <div
              key={index}
              className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4"
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
          <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl border border-dashed border-gray-300 dark:border-gray-600 p-8 text-center">
            <p className="text-gray-500 dark:text-gray-400">
              Click "Generate Style Proposals" to create visual style options for your carousel
            </p>
          </div>
        ) : (
          proposals.map((proposal) => (
            <button
              key={proposal.index}
              onClick={() => onSelect(proposal.index)}
              className={`w-full text-left bg-white dark:bg-gray-800 rounded-lg shadow-sm border-2 p-4 transition-colors ${
                selectedIndex === proposal.index
                  ? 'border-lucid-500 ring-2 ring-lucid-200 dark:ring-lucid-900/50'
                  : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-500'
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
                  src={proposal.preview_image}
                  alt={`Style proposal ${proposal.index + 1}`}
                  className="w-full rounded-lg mb-3"
                  style={{ aspectRatio: '4/5' }}
                />
              )}

              <p className="text-gray-700 dark:text-gray-300 text-sm">{proposal.description}</p>
            </button>
          ))
        )}
      </div>
    </>
  );
}
