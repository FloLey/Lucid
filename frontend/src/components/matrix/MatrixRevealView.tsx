import { useState, useCallback, Fragment } from 'react';
import type { MatrixProject, MatrixCell } from '../../types';
import { getEffectiveDimensions } from '../../utils/matrix';

/** Width of the row-label column in the reveal grid (px) — must match gridTemplateColumns below. */
const ROW_HEADER_W = 80;

type CellRevealStage = 'hidden' | 'name' | 'definition' | 'explanation' | 'image';

function cellKey(row: number, col: number) {
  return `${row}-${col}`;
}

interface MatrixRevealViewProps {
  matrix: MatrixProject;
}

export default function MatrixRevealView({ matrix }: MatrixRevealViewProps) {
  const [revealMap, setRevealMap] = useState<Map<string, CellRevealStage>>(new Map());

  const isDescriptionMode = matrix.input_mode === 'description';
  const { nRows, nCols } = getEffectiveDimensions(matrix);

  const getCell = (row: number, col: number): MatrixCell | undefined =>
    matrix.cells.find((c) => c.row === row && c.col === col);

  const getDiagCell = (i: number) => getCell(i, i);

  const getRowHeader = (row: number): string => {
    if (isDescriptionMode && matrix.row_labels?.length > row) {
      return matrix.row_labels[row];
    }
    return getDiagCell(row)?.row_descriptor ?? getDiagCell(row)?.label ?? `R${row}`;
  };

  const getColHeader = (col: number): string => {
    if (isDescriptionMode && matrix.col_labels?.length > col) {
      return matrix.col_labels[col];
    }
    return getDiagCell(col)?.col_descriptor ?? getDiagCell(col)?.label ?? `C${col}`;
  };

  const getStage = (row: number, col: number): CellRevealStage =>
    revealMap.get(cellKey(row, col)) ?? 'hidden';

  const getNextStage = useCallback(
    (cell: MatrixCell, isDiagonal: boolean, current: CellRevealStage): CellRevealStage => {
      const hasDefinition = isDiagonal && Boolean(cell.definition);
      const hasExplanation = Boolean(cell.explanation);
      const hasImage = Boolean(cell.image_url);

      if (current === 'hidden') return 'name';
      if (current === 'name') {
        if (hasDefinition) return 'definition';
        if (hasExplanation) return 'explanation';
        if (hasImage) return 'image';
        return 'hidden';
      }
      if (current === 'definition') {
        if (hasExplanation) return 'explanation';
        if (hasImage) return 'image';
        return 'hidden';
      }
      if (current === 'explanation') {
        return hasImage ? 'image' : 'hidden';
      }
      return 'hidden'; // image → hidden
    },
    [],
  );

  const handleCellClick = useCallback(
    (cell: MatrixCell) => {
      const isDiagonal = !isDescriptionMode && cell.row === cell.col;
      const current = revealMap.get(cellKey(cell.row, cell.col)) ?? 'hidden';
      const next = getNextStage(cell, isDiagonal, current);
      setRevealMap((prev) => new Map(prev).set(cellKey(cell.row, cell.col), next));
    },
    [revealMap, isDescriptionMode, getNextStage],
  );

  const handleRevealAll = () => {
    const next = new Map<string, CellRevealStage>();
    matrix.cells.forEach((cell) => {
      next.set(cellKey(cell.row, cell.col), 'name');
    });
    setRevealMap(next);
  };

  const handleHideAll = () => {
    setRevealMap(new Map());
  };

  return (
    <div className="flex flex-col gap-3">
      {/* Controls */}
      <div className="flex items-center gap-2 shrink-0">
        <span className="text-xs text-gray-500 dark:text-gray-400">
          Tap to reveal name • definition • explanation • image • hidden
        </span>
        <div className="ml-auto flex gap-2">
          <button
            onClick={handleRevealAll}
            className="px-2 py-1 text-xs text-gray-600 dark:text-gray-300 border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          >
            Reveal all
          </button>
          <button
            onClick={handleHideAll}
            className="px-2 py-1 text-xs text-gray-600 dark:text-gray-300 border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          >
            Hide all
          </button>
        </div>
      </div>

      {/* Grid with axis titles */}
      <div className="flex gap-1">
        {/* Row axis title — vertical rotated text, left of the grid (description mode only) */}
        {isDescriptionMode && matrix.row_axis_title && (
          <div
            className="flex items-center justify-center shrink-0 text-xs font-semibold text-lucid-600 dark:text-lucid-400"
            style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)', width: 16 }}
          >
            {matrix.row_axis_title}
          </div>
        )}
        <div className="flex-1 min-w-0 flex flex-col gap-1">
          {/* Col axis title — horizontal text above column headers (description mode only) */}
          {isDescriptionMode && matrix.col_axis_title && (
            <div
              className="shrink-0 text-xs font-semibold text-lucid-600 dark:text-lucid-400 text-center"
              style={{ paddingLeft: ROW_HEADER_W }}
            >
              {matrix.col_axis_title}
            </div>
          )}
          <div className="overflow-auto">
        <div
          className="grid gap-1 min-w-fit"
          style={{
            gridTemplateColumns: `80px repeat(${nCols}, minmax(90px, 1fr))`,
          }}
        >
          {/* Top-left corner */}
          <div />

          {/* Column headers */}
          {Array.from({ length: nCols }, (_, col) => (
            <div
              key={col}
              className="text-xs font-semibold text-gray-600 dark:text-gray-300 text-center px-1 pb-1 break-words line-clamp-3"
              title={getColHeader(col)}
            >
              {getColHeader(col)}
            </div>
          ))}

          {/* Rows */}
          {Array.from({ length: nRows }, (_, row) => (
            <Fragment key={row}>
              {/* Row label */}
              <div
                key={`label-${row}`}
                className="flex items-center justify-end pr-2 text-xs font-semibold text-gray-600 dark:text-gray-300"
                title={getRowHeader(row)}
              >
                <span className="break-words line-clamp-2 text-right">
                  {getRowHeader(row)}
                </span>
              </div>

              {/* Cells */}
              {Array.from({ length: nCols }, (_, col) => {
                const cell = getCell(row, col);
                if (!cell) {
                  return (
                    <div
                      key={col}
                      className="aspect-square bg-gray-100 dark:bg-gray-800 rounded-lg"
                    />
                  );
                }
                const stage = getStage(row, col);
                return (
                  <RevealCell
                    key={col}
                    cell={cell}
                    isDiagonal={!isDescriptionMode && row === col}
                    stage={stage}
                    onClick={() => handleCellClick(cell)}
                  />
                );
              })}
            </Fragment>
          ))}
        </div>
          </div>
        </div>
      </div>
    </div>
  );
}

interface RevealCellProps {
  cell: MatrixCell;
  isDiagonal: boolean;
  stage: CellRevealStage;
  onClick: () => void;
}

function RevealCell({ cell, isDiagonal, stage, onClick }: RevealCellProps) {
  if (stage === 'hidden') {
    return (
      <button
        onClick={onClick}
        className="aspect-square rounded-lg bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors cursor-pointer border-2 border-dashed border-gray-300 dark:border-gray-600"
        title="Tap to reveal"
      />
    );
  }

  // Image stage
  if (stage === 'image' && cell.image_url) {
    return (
      <button
        onClick={onClick}
        className="aspect-square rounded-lg overflow-hidden relative cursor-pointer"
        style={{
          backgroundImage: `url(${cell.image_url})`,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
        }}
      >
        <div className="absolute inset-0 bg-black/30 flex items-center justify-center p-2">
          <span
            className="text-white text-xs font-bold text-center leading-tight"
            style={{
              textShadow:
                '1px 1px 2px black, -1px -1px 2px black, 1px -1px 2px black, -1px 1px 2px black',
            }}
          >
            {isDiagonal ? cell.label : cell.concept}
          </span>
        </div>
      </button>
    );
  }

  // Definition stage (theme-mode diagonal cells only)
  if (stage === 'definition') {
    return (
      <button
        onClick={onClick}
        className="aspect-square rounded-lg p-2 cursor-pointer bg-lucid-50 dark:bg-lucid-900/30 hover:bg-lucid-100 dark:hover:bg-lucid-800/40 border border-lucid-200 dark:border-lucid-700 flex items-center justify-center"
      >
        <span className="text-xs text-gray-600 dark:text-gray-300 text-center leading-tight line-clamp-4">
          {cell.definition}
        </span>
      </button>
    );
  }

  // Explanation stage
  if (stage === 'explanation') {
    return (
      <button
        onClick={onClick}
        className="aspect-square rounded-lg p-2 cursor-pointer bg-gray-50 dark:bg-gray-700/50 hover:bg-gray-100 dark:hover:bg-gray-700 border border-gray-200 dark:border-gray-600 flex items-center justify-center"
      >
        <span className="text-xs text-gray-600 dark:text-gray-300 text-center leading-tight line-clamp-4">
          {cell.explanation}
        </span>
      </button>
    );
  }

  // Name stage: show label (diagonal) or concept (off-diagonal)
  const text = isDiagonal ? cell.label : cell.concept;
  return (
    <button
      onClick={onClick}
      className={`aspect-square rounded-lg p-2 cursor-pointer flex items-center justify-center transition-colors ${
        isDiagonal
          ? 'bg-lucid-100 dark:bg-lucid-900/40 hover:bg-lucid-200 dark:hover:bg-lucid-800/40 border border-lucid-200 dark:border-lucid-700'
          : 'bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 border border-gray-200 dark:border-gray-600'
      }`}
    >
      <span className="text-xs font-semibold text-gray-900 dark:text-white text-center leading-tight line-clamp-3">
        {text}
      </span>
    </button>
  );
}
