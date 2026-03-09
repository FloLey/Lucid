import type { MatrixProject } from '../../types';

interface MatrixAxisTitlesProps {
  matrix: MatrixProject;
  paddingLeft: number;
}

/** Renders the row × col axis title bar in description mode. Returns null otherwise. */
export default function MatrixAxisTitles({ matrix, paddingLeft }: MatrixAxisTitlesProps) {
  if (matrix.input_mode !== 'description' || (!matrix.row_axis_title && !matrix.col_axis_title)) {
    return null;
  }
  return (
    <div className="flex items-center gap-2 text-xs mb-1" style={{ paddingLeft }}>
      {matrix.row_axis_title && (
        <span className="font-semibold text-lucid-600 dark:text-lucid-400">{matrix.row_axis_title}</span>
      )}
      {matrix.row_axis_title && matrix.col_axis_title && (
        <span className="text-gray-400 dark:text-gray-500">×</span>
      )}
      {matrix.col_axis_title && (
        <span className="font-semibold text-lucid-600 dark:text-lucid-400">{matrix.col_axis_title}</span>
      )}
    </div>
  );
}
