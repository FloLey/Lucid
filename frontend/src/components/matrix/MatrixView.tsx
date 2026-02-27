import { useState, useCallback, useEffect } from 'react';
import type { MatrixProject, MatrixCell as MatrixCellType } from '../../types';
import MatrixCell from './MatrixCell';
import { useMatrixStream } from '../../hooks/useMatrixStream';
import { useMatrix } from '../../contexts/MatrixContext';
import * as api from '../../services/api';
import { getErrorMessage } from '../../utils/error';

interface MatrixViewProps {
  matrix: MatrixProject;
}

export default function MatrixView({ matrix: initialMatrix }: MatrixViewProps) {
  const { updateMatrix, closeMatrix } = useMatrix();
  const [matrix, setMatrix] = useState<MatrixProject>(initialMatrix);
  const [selectedCell, setSelectedCell] = useState<MatrixCellType | null>(null);
  const [streamError, setStreamError] = useState<string | null>(null);
  const [regenInstructions, setRegenInstructions] = useState('');
  const [regenLoading, setRegenLoading] = useState(false);

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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialMatrix.id]);

  const n = matrix.n;

  const getCell = (row: number, col: number): MatrixCellType | undefined =>
    matrix.cells.find((c) => c.row === row && c.col === col);

  const getDiagCell = (i: number) => getCell(i, i);

  const completedCells = matrix.cells.filter((c) => c.cell_status === 'complete').length;
  const totalCells = n * n;

  const handleCellClick = (cell: MatrixCellType) => {
    setSelectedCell((prev) => (prev?.id === cell.id ? null : cell));
    setRegenInstructions('');
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
      // Refresh selected cell
      const refreshed = updated.cells.find(
        (c) => c.row === selectedCell.row && c.col === selectedCell.col
      );
      if (refreshed) setSelectedCell(refreshed);
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
      const refreshed = updated.cells.find(
        (c) => c.row === selectedCell.row && c.col === selectedCell.col
      );
      if (refreshed) setSelectedCell(refreshed);
    } catch (err) {
      setStreamError(getErrorMessage(err, 'Image regeneration failed'));
    } finally {
      setRegenLoading(false);
    }
  };

  const selectedIsDiagonal = selectedCell
    ? selectedCell.row === selectedCell.col
    : false;

  return (
    <div className="flex flex-col gap-4 h-full">
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

      {/* Grid + detail panel */}
      <div className="flex gap-4 min-h-0 flex-1">
        {/* Grid */}
        <div className="flex-1 min-w-0 overflow-auto">
          <div
            className="grid gap-1 min-w-fit"
            style={{
              gridTemplateColumns: `64px repeat(${n}, minmax(80px, 1fr))`,
            }}
          >
            {/* Top-left corner */}
            <div />
            {/* Column headers */}
            {Array.from({ length: n }, (_, i) => {
              const dc = getDiagCell(i);
              return (
                <div
                  key={i}
                  className="text-xs font-medium text-gray-500 dark:text-gray-400 text-center px-1 pb-1 truncate"
                  title={dc?.col_descriptor ?? dc?.label ?? ''}
                >
                  {dc?.col_descriptor || dc?.label || `C${i}`}
                </div>
              );
            })}

            {/* Row + cells */}
            {Array.from({ length: n }, (_, row) => (
              <>
                {/* Row label */}
                <div
                  key={`label-${row}`}
                  className="flex items-center justify-end pr-2 text-xs font-medium text-gray-500 dark:text-gray-400 truncate"
                  title={getDiagCell(row)?.row_descriptor ?? getDiagCell(row)?.label ?? ''}
                >
                  {getDiagCell(row)?.row_descriptor || getDiagCell(row)?.label || `R${row}`}
                </div>
                {Array.from({ length: n }, (_, col) => {
                  const cell = getCell(row, col);
                  if (!cell) return <div key={col} className="aspect-square" />;
                  return (
                    <MatrixCell
                      key={col}
                      cell={cell}
                      isDiagonal={row === col}
                      rowLabel={getDiagCell(row)?.row_descriptor ?? getDiagCell(row)?.label ?? ''}
                      colLabel={getDiagCell(col)?.col_descriptor ?? getDiagCell(col)?.label ?? ''}
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
            <div>
              <h3 className="font-semibold text-gray-900 dark:text-white">
                {selectedIsDiagonal ? selectedCell.label : selectedCell.concept}
              </h3>
              {selectedIsDiagonal ? (
                <>
                  <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">
                    {selectedCell.definition}
                  </p>
                  {selectedCell.row_descriptor && (
                    <div className="mt-2 text-xs text-gray-400 dark:text-gray-500">
                      <span className="font-medium">Row axis:</span> {selectedCell.row_descriptor}
                    </div>
                  )}
                  {selectedCell.col_descriptor && (
                    <div className="text-xs text-gray-400 dark:text-gray-500">
                      <span className="font-medium">Col axis:</span> {selectedCell.col_descriptor}
                    </div>
                  )}
                </>
              ) : (
                <>
                  <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">
                    {selectedCell.explanation}
                  </p>
                  <div className="mt-3 space-y-1 text-xs text-gray-400 dark:text-gray-500">
                    {(() => {
                      const rowDiag = getDiagCell(selectedCell.row);
                      const colDiag = getDiagCell(selectedCell.col);
                      return (
                        <>
                          {rowDiag && (
                            <div>
                              <span className="font-medium text-gray-500 dark:text-gray-400">Row:</span>{' '}
                              {rowDiag.label}{rowDiag.row_descriptor ? ` — ${rowDiag.row_descriptor}` : ''}
                            </div>
                          )}
                          {colDiag && (
                            <div>
                              <span className="font-medium text-gray-500 dark:text-gray-400">Col:</span>{' '}
                              {colDiag.label}{colDiag.col_descriptor ? ` — ${colDiag.col_descriptor}` : ''}
                            </div>
                          )}
                        </>
                      );
                    })()}
                  </div>
                </>
              )}
            </div>

            {selectedCell.image_url && (
              <img
                src={selectedCell.image_url}
                alt=""
                className="rounded-lg w-full object-cover"
              />
            )}

            {/* Actions */}
            {!selectedIsDiagonal && (
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
                {matrix.include_images && (
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
