import type { MatrixCell as MatrixCellType } from '../../types';

interface MatrixCellProps {
  cell: MatrixCellType;
  isDiagonal: boolean;
  rowLabel: string;
  colLabel: string;
  onClick: () => void;
  isSelected: boolean;
}

export default function MatrixCell({
  cell,
  isDiagonal,
  rowLabel,
  colLabel,
  onClick,
  isSelected,
}: MatrixCellProps) {
  const isPending = cell.cell_status === 'pending';
  const isGenerating = cell.cell_status === 'generating';
  const isFailed = cell.cell_status === 'failed';
  const isComplete = cell.cell_status === 'complete';

  const primaryText = isDiagonal ? cell.label : cell.concept;
  const secondaryText = isDiagonal ? cell.definition : cell.explanation;

  return (
    <button
      onClick={onClick}
      className={[
        'group relative w-full aspect-square rounded-lg border text-left transition-all duration-300 overflow-hidden',
        isDiagonal
          ? 'bg-lucid-50 dark:bg-lucid-900/20 border-lucid-300 dark:border-lucid-700'
          : 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700',
        isSelected
          ? 'ring-2 ring-lucid-500 border-lucid-400'
          : 'hover:border-lucid-300 dark:hover:border-lucid-600 hover:shadow-sm',
        isPending ? 'opacity-40' : '',
        isComplete ? 'opacity-100' : '',
      ].join(' ')}
    >
      {/* Background image */}
      {cell.image_url && (
        <img
          src={cell.image_url}
          alt=""
          className="absolute inset-0 w-full h-full object-cover"
        />
      )}

      {/* Text overlay — shown always (no image) or on hover (with image) */}
      <div
        className={[
          'absolute inset-0 p-2 flex flex-col justify-start transition-opacity duration-200',
          cell.image_url
            ? 'opacity-0 group-hover:opacity-100 bg-black/70'
            : '',
        ].join(' ')}
      >
        {primaryText ? (
          <>
            <p
              className={[
                'font-semibold leading-tight text-xs',
                cell.image_url
                  ? 'text-white'
                  : isDiagonal
                    ? 'text-lucid-700 dark:text-lucid-300'
                    : 'text-gray-800 dark:text-gray-100',
              ].join(' ')}
            >
              {primaryText}
            </p>
            {secondaryText && (
              <p
                className={[
                  'text-xs mt-0.5 line-clamp-3',
                  cell.image_url ? 'text-gray-200' : 'text-gray-500 dark:text-gray-400',
                ].join(' ')}
              >
                {secondaryText}
              </p>
            )}
            {!isDiagonal && (cell.image_url || isSelected) && (
              <div className="mt-auto pt-1 text-xs text-gray-400 dark:text-gray-500 space-y-0.5">
                <div className="truncate">↔ {colLabel}</div>
                <div className="truncate">↕ {rowLabel}</div>
              </div>
            )}
          </>
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            {isPending && (
              <div className="w-4 h-4 rounded-full bg-gray-200 dark:bg-gray-600 animate-pulse" />
            )}
          </div>
        )}
      </div>

      {/* Status indicators */}
      {isGenerating && (
        <div className="absolute top-1 right-1 z-10">
          <svg className="w-3 h-3 animate-spin text-lucid-500" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        </div>
      )}

      {isFailed && (
        <div className="absolute top-1 right-1 z-10 w-3 h-3 rounded-full bg-red-500" title={cell.cell_error || 'Failed'} />
      )}
    </button>
  );
}
