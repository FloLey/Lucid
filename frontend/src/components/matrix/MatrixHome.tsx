import { useState } from 'react';
import { useMatrix } from '../../contexts/MatrixContext';
import NewMatrixModal from './NewMatrixModal';
import type { CreateMatrixParams } from '../../services/api';

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;
  return date.toLocaleDateString();
}

const STATUS_BADGE: Record<string, { label: string; cls: string }> = {
  pending: { label: 'Pending', cls: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300' },
  generating: { label: 'Generating…', cls: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300' },
  complete: { label: 'Done', cls: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300' },
  failed: { label: 'Failed', cls: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300' },
};

interface MatrixHomeProps {
  onOpenSettings: () => void;
}

export default function MatrixHome({ onOpenSettings }: MatrixHomeProps) {
  const { matrices, matricesLoading, openMatrix, createMatrix, deleteMatrix } = useMatrix();
  const [showNewModal, setShowNewModal] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const handleCreate = async (params: CreateMatrixParams) => {
    await createMatrix(params);
    setShowNewModal(false);
  };

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (!confirm('Delete this matrix? This cannot be undone.')) return;
    setDeletingId(id);
    try {
      await deleteMatrix(id);
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="px-6 py-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Concept Matrices</h2>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            Generate n×n matrices of interconnected concepts for any theme.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={onOpenSettings}
            className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            Settings
          </button>
          <button
            onClick={() => setShowNewModal(true)}
            className="flex items-center gap-2 px-5 py-2.5 bg-lucid-600 text-white font-medium rounded-lg hover:bg-lucid-700 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            New Matrix
          </button>
        </div>
      </div>

      {/* Content */}
      {matricesLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div
              key={i}
              className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 animate-pulse space-y-3"
            >
              <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4" />
              <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/2" />
              <div className="grid grid-cols-3 gap-1.5 mt-4">
                {Array.from({ length: 9 }).map((_, j) => (
                  <div key={j} className="h-8 bg-gray-100 dark:bg-gray-700 rounded" />
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : matrices.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <div className="w-20 h-20 bg-lucid-50 dark:bg-lucid-900/20 rounded-2xl flex items-center justify-center mb-4">
            <svg className="w-10 h-10 text-lucid-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 5a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H5a1 1 0 01-1-1V5zm10 0a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1V5zM4 15a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H5a1 1 0 01-1-1v-4zm10 0a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">No matrices yet</h3>
          <p className="text-gray-500 dark:text-gray-400 mb-6 max-w-sm">
            Create your first concept matrix to explore relationships between ideas.
          </p>
          <button
            onClick={() => setShowNewModal(true)}
            className="px-6 py-3 bg-lucid-600 text-white font-medium rounded-lg hover:bg-lucid-700 transition-colors"
          >
            Create your first matrix
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {matrices.map((matrix) => {
            const badge = STATUS_BADGE[matrix.status] ?? STATUS_BADGE.pending;

            return (
              <div
                key={matrix.id}
                onClick={() => openMatrix(matrix.id)}
                className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 cursor-pointer hover:shadow-md hover:border-lucid-300 dark:hover:border-lucid-600 transition-all group relative"
              >
                {/* Delete button */}
                <button
                  onClick={(e) => handleDelete(e, matrix.id)}
                  disabled={deletingId === matrix.id}
                  className="absolute top-3 right-3 w-7 h-7 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 hover:bg-red-50 dark:hover:bg-red-900/30 transition-all"
                  title="Delete matrix"
                >
                  {deletingId === matrix.id ? (
                    <svg className="w-3.5 h-3.5 text-gray-400 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                  ) : (
                    <svg className="w-3.5 h-3.5 text-gray-500 hover:text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  )}
                </button>

                {/* Name / theme */}
                <h3 className="font-semibold text-gray-900 dark:text-gray-100 truncate pr-8 text-sm">
                  {matrix.name || matrix.theme}
                </h3>
                {matrix.name && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 truncate mt-0.5">{matrix.theme}</p>
                )}

                {/* Mini grid preview */}
                <div
                  className="mt-3 grid gap-1"
                  style={{ gridTemplateColumns: `repeat(${matrix.n}, 1fr)` }}
                >
                  {Array.from({ length: matrix.n * matrix.n }).map((_, idx) => (
                    <div
                      key={idx}
                      className="h-5 rounded-sm bg-lucid-100 dark:bg-lucid-900/30"
                    />
                  ))}
                </div>

                {/* Footer */}
                <div className="flex items-center justify-between mt-3">
                  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${badge.cls}`}>
                    {badge.label}
                  </span>
                  <span className="text-xs text-gray-400 dark:text-gray-500">{formatDate(matrix.updated_at)}</span>
                </div>

              </div>
            );
          })}
        </div>
      )}

      {showNewModal && (
        <NewMatrixModal
          onClose={() => setShowNewModal(false)}
          onCreate={handleCreate}
        />
      )}
    </div>
  );
}
