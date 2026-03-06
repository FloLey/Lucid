import type { MatrixProject } from '../types';

/** Returns the effective grid dimensions for a matrix project.
 *
 * Description-mode matrices store explicit n_rows/n_cols; theme-mode
 * matrices are always square with side length n.
 */
export function getEffectiveDimensions(matrix: Pick<MatrixProject, 'input_mode' | 'n' | 'n_rows' | 'n_cols'>): {
  nRows: number;
  nCols: number;
} {
  const isDescriptionMode = matrix.input_mode === 'description';
  return {
    nRows: isDescriptionMode && matrix.n_rows > 0 ? matrix.n_rows : matrix.n,
    nCols: isDescriptionMode && matrix.n_cols > 0 ? matrix.n_cols : matrix.n,
  };
}
