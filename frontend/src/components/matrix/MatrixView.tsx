import { useState, useCallback, useEffect } from 'react';
import type { MatrixProject, MatrixCell as MatrixCellType } from '../../types';
import MatrixCell from './MatrixCell';
import MatrixRevealView from './MatrixRevealView';
import MatrixPosterView from './MatrixPosterView';
import { useMatrixStream } from '../../hooks/useMatrixStream';
import { useMatrix } from '../../contexts/MatrixContext';
import * as api from '../../services/api';
import { getErrorMessage } from '../../utils/error';
import { getEffectiveDimensions } from '../../utils/matrix';

type ViewMode = 'edit' | 'reveal' | 'poster';

interface MatrixViewProps {
  matrix: MatrixProject;
}

export default function MatrixView({ matrix: initialMatrix }: MatrixViewProps) {
  const { updateMatrix, closeMatrix } = useMatrix();
  const [matrix, setMatrix] = useState<MatrixProject>(initialMatrix);
  const [selectedCell, setSelectedCell] = useState<MatrixCellType | null>(null);
  const [streamError, setStreamError] = useState<string | null>(
    initialMatrix.status === 'failed'
      ? (initialMatrix.error_message ?? 'Generation failed')
      : null
  );
  const [regenInstructions, setRegenInstructions] = useState('');
  const [regenLoading, setRegenLoading] = useState(false);
  const [imgGenLoading, setImgGenLoading] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>('edit');

  const handleUpdate = useCallback(
    (updater: (prev: MatrixProject) => MatrixProject) => {
      setMatrix((prev) => {
        const next = updater(prev);
        updateMatrix(next);
        return next;
      });
    },
    [updateMatrix],
  );

  const { isStreaming, startStream } = useMatrixStream({
    onUpdate: handleUpdate,
    onComplete: () => {
      api.getMatrix(matrix.id).then((m) => {
        setMatrix(m);
        updateMatrix(m);
      }).catch(console.error);
    },
    onError: (msg) => setStreamError(msg),
  });

  // Auto-start stream when project is generating
  useEffect(() => {
    if (initialMatrix.status === 'generating') {
      startStream(initialMatrix.id);
    }
  }, [initialMatrix.id, initialMatrix.status, startStream]);

  const isDescriptionMode = matrix.input_mode === 'description';
  const { nRows, nCols } = getEffectiveDimensions(matrix);

  const getCell = (row: number, col: number): MatrixCellType | undefined =>
    matrix.cells.find((c) => c.row === row && c.col === col);

  const getDiagCell = (i: number) => getCell(i, i);

  /** Row header for row i — uses row_labels in description mode, diagonal cell otherwise. */
  const getRowHeader = (row: number): string => {
    if (isDescriptionMode && matrix.row_labels?.length > row) {
      return matrix.row_labels[row];
    }
    return getDiagCell(row)?.row_descriptor ?? getDiagCell(row)?.label ?? `R${row}`;
  };

  /** Col header for col j — uses col_labels in description mode, diagonal cell otherwise. */
  const getColHeader = (col: number): string => {
    if (isDescriptionMode && matrix.col_labels?.length > col) {
      return matrix.col_labels[col];
    }
    return getDiagCell(col)?.col_descriptor ?? getDiagCell(col)?.label ?? `C${col}`;
  };

  const completedCells = matrix.cells.filter((c) => c.cell_status === 'complete').length;
  const totalCells = nRows * nCols;

  const handleCellClick = (cell: MatrixCellType) => {
    setSelectedCell((prev) => (prev?.id === cell.id ? null : cell));
    setRegenInstructions('');
  };

  const refreshSelectedCell = (updated: MatrixProject) => {
    const refreshed = updated.cells.find(
      (c) => c.row === selectedCell?.row && c.col === selectedCell?.col
    );
    if (refreshed) setSelectedCell(refreshed);
  };

  const handleRegenerate = async () => {
    if (!selectedCell || selectedCell.row === selectedCell.col) return;
    setRegenLoading(true);
    try {
      const updated = await api.regenerateMatrixCell(
        matrix.id,
        selectedCell.row,
        selectedCell.col,
        regenInstructions || undefined,
      );
      setMatrix(updated);
      updateMatrix(updated);
      refreshSelectedCell(updated);
    } catch (err) {
      setStreamError(getErrorMessage(err, 'Regeneration failed'));
    } finally {
      setRegenLoading(false);
    }
  };

  const handleRegenerateImage = async () => {
    if (!selectedCell) return;
    setRegenLoading(true);
    try {
      const updated = await api.regenerateMatrixCell(
        matrix.id,
        selectedCell.row,
        selectedCell.col,
        undefined,
        true,
      );
      setMatrix(updated);
      updateMatrix(updated);
      refreshSelectedCell(updated);
    } catch (err) {
      setStreamError(getErrorMessage(err, 'Image regeneration failed'));
    } finally {
      setRegenLoading(false);
    }
  };

  const handleGenerateAllImages = async () => {
    setImgGenLoading(true);
    try {
      await api.generateMatrixImages(matrix.id);
      startStream(matrix.id);
    } catch (err) {
      setStreamError(getErrorMessage(err, 'Failed to start image generation'));
    } finally {
      setImgGenLoading(false);
    }
  };

  // In description mode all cells are intersections — none are "diagonal concept seeds"
  const selectedIsDiagonal = selectedCell
    ? !isDescriptionMode && selectedCell.row === selectedCell.col
    : false;

  return (
    <div className="flex flex-col gap-4 h-full p-4">
      {/* Toolbar */}
      <div className="flex items-center justify-between shrink-0">
        <div>
          <h2 className="text-xl font-bold text-gray-900 dark:text-white leading-tight">
            {matrix.name}
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{matrix.theme}</p>
        </div>
        <div className="flex items-center gap-3">
          {isStreaming && (
            <div className="flex items-center gap-1.5 text-sm text-lucid-600 dark:text-lucid-400">
              <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Generating…
            </div>
          )}
          {matrix.status === 'complete' && !isStreaming &&
            matrix.cells.some((c) => c.cell_status === 'complete' && !c.image_url) && (
            <button
              onClick={handleGenerateAllImages}
              disabled={imgGenLoading}
              className="px-3 py-1.5 text-xs font-medium text-lucid-600 dark:text-lucid-400 border border-lucid-300 dark:border-lucid-700 rounded-lg hover:bg-lucid-50 dark:hover:bg-lucid-900/30 disabled:opacity-50 transition-colors"
            >
              {imgGenLoading ? 'Starting…' : '+ Generate images'}
            </button>
          )}
          {matrix.status === 'complete' && (
            <div className="flex rounded-lg border border-gray-300 dark:border-gray-600 overflow-hidden text-xs font-medium">
              {(['edit', 'reveal', 'poster'] as ViewMode[]).map((mode) => (
                <button
                  key={mode}
                  onClick={() => setViewMode(mode)}
                  className={`px-3 py-1.5 capitalize transition-colors ${
                    viewMode === mode
                      ? 'bg-lucid-600 text-white'
                      : 'text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
                  }`}
                >
                  {mode}
                </button>
              ))}
            </div>
          )}
          <button
            onClick={closeMatrix}
            className="px-3 py-1.5 text-sm text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          >
            ← Back
          </button>
        </div>
      </div>

      {/* Progress bar */}
      {(isStreaming || matrix.status === 'generating') && (
        <div className="shrink-0">
          <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mb-1">
            <span>Generating cells…</span>
            <span>{completedCells} / {totalCells}</span>
          </div>
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
            <div
              className="bg-lucid-500 h-1.5 rounded-full transition-all duration-500"
              style={{ width: `${(completedCells / totalCells) * 100}%` }}
            />
          </div>
        </div>
      )}

      {streamError && (
        <div className="shrink-0 p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 rounded-lg text-sm flex items-start gap-2">
          <span className="flex-1">{streamError}</span>
          <button onClick={() => setStreamError(null)} className="shrink-0 text-red-400 hover:text-red-600">✕</button>
        </div>
      )}

      {/* Alternate views */}
      {viewMode === 'reveal' && <MatrixRevealView matrix={matrix} />}
      {viewMode === 'poster' && <MatrixPosterView matrix={matrix} />}

      {/* Grid + detail panel (edit view) */}
      <div className={`flex gap-4 min-h-0 flex-1 ${viewMode !== 'edit' ? 'hidden' : ''}`}>
        {/* Grid */}
        <div className="flex-1 min-w-0 overflow-auto">
          <div
            className="grid gap-1 min-w-fit"
            style={{
              gridTemplateColumns: `64px repeat(${nCols}, minmax(80px, 1fr))`,
            }}
          >
            {/* Top-left corner */}
            <div />
            {/* Column headers */}
            {Array.from({ length: nCols }, (_, col) => (
              <div
                key={col}
                className="text-xs font-medium text-gray-500 dark:text-gray-400 text-center px-1 pb-1 truncate"
                title={getColHeader(col)}
              >
                {getColHeader(col)}
              </div>
            ))}

            {/* Row + cells */}
            {Array.from({ length: nRows }, (_, row) => (
              <>
                {/* Row label */}
                <div
                  key={`label-${row}`}
                  className="flex items-center justify-end pr-2 text-xs font-medium text-gray-500 dark:text-gray-400 truncate"
                  title={getRowHeader(row)}
                >
                  {getRowHeader(row)}
                </div>
                {Array.from({ length: nCols }, (_, col) => {
                  const cell = getCell(row, col);
                  if (!cell) return <div key={col} className="aspect-square" />;
                  return (
                    <MatrixCell
                      key={col}
                      cell={cell}
                      isDiagonal={!isDescriptionMode && row === col}
                      rowLabel={getRowHeader(row)}
                      colLabel={getColHeader(col)}
                      isSelected={selectedCell?.id === cell.id}
                      onClick={() => handleCellClick(cell)}
                    />
                  );
                })}
              </>
            ))}
          </div>
        </div>

        {/* Detail panel */}
        {selectedCell && (
          <div className="w-72 shrink-0 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-4 overflow-y-auto flex flex-col gap-3">
            {/* Header with close button */}
            <div className="flex items-start justify-between gap-2">
              <h3 className="font-semibold text-gray-900 dark:text-white leading-snug">
                {selectedIsDiagonal ? selectedCell.label : selectedCell.concept}
              </h3>
              <button
                onClick={() => setSelectedCell(null)}
                className="shrink-0 p-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors"
                aria-label="Close"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {selectedIsDiagonal ? (
              <>
                <p className="text-sm text-gray-600 dark:text-gray-300 -mt-1">
                  {selectedCell.definition}
                </p>
                {selectedCell.row_descriptor && (
                  <div className="text-xs text-gray-400 dark:text-gray-400">
                    <span className="font-medium">Row axis:</span> {selectedCell.row_descriptor}
                  </div>
                )}
                {selectedCell.col_descriptor && (
                  <div className="text-xs text-gray-400 dark:text-gray-400">
                    <span className="font-medium">Col axis:</span> {selectedCell.col_descriptor}
                  </div>
                )}
                {isDescriptionMode && selectedCell.explanation && (
                  <div>
                    <p className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wide mb-1">Reasoning</p>
                    <p className="text-sm text-gray-600 dark:text-gray-300">
                      {selectedCell.explanation}
                    </p>
                  </div>
                )}
              </>
            ) : (
              <>
                {/* Axis position — row & col with their quality descriptors */}
                <div className="space-y-1 text-xs bg-gray-50 dark:bg-gray-700/50 rounded-lg p-2.5">
                  {(() => {
                    if (isDescriptionMode) {
                      const rowLabel = matrix.row_labels?.[selectedCell.row];
                      const colLabel = matrix.col_labels?.[selectedCell.col];
                      return (
                        <>
                          {rowLabel && (
                            <div className="text-gray-500 dark:text-gray-400">
                              <span className="font-medium text-gray-600 dark:text-gray-300">Row:</span>{' '}
                              {rowLabel}
                              {selectedCell.row_descriptor && (
                                <span className="text-gray-400 dark:text-gray-500"> — {selectedCell.row_descriptor}</span>
                              )}
                            </div>
                          )}
                          {colLabel && (
                            <div className="text-gray-500 dark:text-gray-400">
                              <span className="font-medium text-gray-600 dark:text-gray-300">Col:</span>{' '}
                              {colLabel}
                              {selectedCell.col_descriptor && (
                                <span className="text-gray-400 dark:text-gray-500"> — {selectedCell.col_descriptor}</span>
                              )}
                            </div>
                          )}
                        </>
                      );
                    }
                    const rowDiag = getDiagCell(selectedCell.row);
                    const colDiag = getDiagCell(selectedCell.col);
                    return (
                      <>
                        {rowDiag && (
                          <div className="text-gray-500 dark:text-gray-400">
                            <span className="font-medium text-gray-600 dark:text-gray-300">Row:</span>{' '}
                            {rowDiag.label}
                            {(selectedCell.row_descriptor || rowDiag.row_descriptor) && (
                              <span className="text-gray-400 dark:text-gray-500"> — {selectedCell.row_descriptor || rowDiag.row_descriptor}</span>
                            )}
                          </div>
                        )}
                        {colDiag && (
                          <div className="text-gray-500 dark:text-gray-400">
                            <span className="font-medium text-gray-600 dark:text-gray-300">Col:</span>{' '}
                            {colDiag.label}
                            {(selectedCell.col_descriptor || colDiag.col_descriptor) && (
                              <span className="text-gray-400 dark:text-gray-500"> — {selectedCell.col_descriptor || colDiag.col_descriptor}</span>
                            )}
                          </div>
                        )}
                      </>
                    );
                  })()}
                </div>

                {/* Reasoning — why this concept fits this position */}
                {selectedCell.explanation && (
                  <div>
                    <p className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wide mb-1">Reasoning</p>
                    <p className="text-sm text-gray-600 dark:text-gray-300">
                      {selectedCell.explanation}
                    </p>
                  </div>
                )}

                {/* Cell error */}
                {selectedCell.cell_error && (
                  <div className="text-xs text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 rounded-lg p-2">
                    <span className="font-medium">Error:</span> {selectedCell.cell_error}
                  </div>
                )}
              </>
            )}

            {selectedCell.image_url && (
              <img
                src={selectedCell.image_url}
                alt=""
                className="rounded-lg w-full object-cover"
              />
            )}

            {/* Actions */}
            {(isDescriptionMode || !selectedIsDiagonal) && (
              <div className="flex flex-col gap-2 mt-auto">
                <textarea
                  value={regenInstructions}
                  onChange={(e) => setRegenInstructions(e.target.value)}
                  placeholder="Extra instructions (optional)…"
                  rows={2}
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-2 py-1.5 text-xs text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-lucid-500 resize-none"
                />
                <button
                  onClick={handleRegenerate}
                  disabled={regenLoading}
                  className="w-full px-3 py-1.5 bg-lucid-600 text-white text-xs font-medium rounded-lg hover:bg-lucid-700 disabled:opacity-50 transition-colors"
                >
                  {regenLoading ? 'Regenerating…' : 'Regenerate concept'}
                </button>
                {selectedCell.image_url && (
                  <button
                    onClick={handleRegenerateImage}
                    disabled={regenLoading}
                    className="w-full px-3 py-1.5 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 text-xs font-medium rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 transition-colors"
                  >
                    Regenerate image
                  </button>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
