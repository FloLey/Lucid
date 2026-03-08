import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import MatrixView from '../matrix/MatrixView';
import type { MatrixCell, MatrixProject } from '../../types';

// ── Module mocks ───────────────────────────────────────────────────────────────

vi.mock('../../contexts/MatrixContext', () => ({
  useMatrix: () => ({
    updateMatrix: vi.fn(),
    closeMatrix: vi.fn(),
  }),
}));

const mockStartStream = vi.fn();
vi.mock('../../hooks/useMatrixStream', () => ({
  useMatrixStream: () => ({
    isStreaming: false,
    startStream: mockStartStream,
  }),
}));

const mockGenerateMatrixImages = vi.fn();
vi.mock('../../services/api', () => ({
  generateMatrixImages: (...args: unknown[]) => mockGenerateMatrixImages(...args),
  getMatrix: vi.fn(),
  regenerateMatrixCell: vi.fn(),
}));

// ── Factory helpers ────────────────────────────────────────────────────────────

function makeCell(
  row: number,
  col: number,
  overrides: Partial<MatrixCell> = {},
): MatrixCell {
  const isDiag = row === col;
  return {
    id: `cell-${row}-${col}`,
    project_id: 'proj-1',
    row,
    col,
    label: isDiag ? `Label${row}` : null,
    definition: isDiag ? `Def${row}` : null,
    row_descriptor: isDiag ? `RowDesc${row}` : null,
    col_descriptor: isDiag ? `ColDesc${row}` : null,
    concept: !isDiag ? `Concept${row}x${col}` : null,
    explanation: !isDiag ? `Exp${row}x${col}` : null,
    image_url: null,
    cell_status: 'complete',
    cell_error: null,
    attempts: 1,
    ...overrides,
  };
}

function makeMatrix(overrides: Partial<MatrixProject> = {}): MatrixProject {
  const n = 2;
  const cells: MatrixCell[] = [];
  for (let r = 0; r < n; r++) {
    for (let c = 0; c < n; c++) {
      cells.push(makeCell(r, c));
    }
  }
  return {
    id: 'proj-1',
    name: 'Test Matrix',
    theme: 'AI Ethics',
    n,
    n_rows: 0,
    n_cols: 0,
    row_labels: [],
    col_labels: [],
    language: 'English',
    style_mode: 'neutral',
    include_images: false,
    input_mode: 'theme',
    description: null,
    status: 'complete',
    error_message: null,
    cells,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  mockGenerateMatrixImages.mockResolvedValue(undefined);
});

// ── Tests ──────────────────────────────────────────────────────────────────────

describe('MatrixView — Generate images button', () => {
  it('shows "+ Generate images" when matrix is complete and cells lack images', () => {
    render(<MatrixView matrix={makeMatrix()} />);
    expect(screen.getByRole('button', { name: /\+ Generate images/i })).toBeInTheDocument();
  });

  it('hides button when all cells already have images', () => {
    const matrix = makeMatrix();
    matrix.cells = matrix.cells.map((c) => ({ ...c, image_url: '/img/x.jpg' }));
    render(<MatrixView matrix={matrix} />);
    expect(screen.queryByRole('button', { name: /\+ Generate images/i })).not.toBeInTheDocument();
  });

  it('hides button when matrix is still generating', () => {
    render(<MatrixView matrix={makeMatrix({ status: 'generating' })} />);
    expect(screen.queryByRole('button', { name: /\+ Generate images/i })).not.toBeInTheDocument();
  });

  it('calls generateMatrixImages and startStream when button is clicked', async () => {
    render(<MatrixView matrix={makeMatrix()} />);
    fireEvent.click(screen.getByRole('button', { name: /\+ Generate images/i }));
    await waitFor(() => {
      expect(mockGenerateMatrixImages).toHaveBeenCalledWith('proj-1');
      expect(mockStartStream).toHaveBeenCalledWith('proj-1');
    });
  });

  it('shows error when generateMatrixImages rejects', async () => {
    mockGenerateMatrixImages.mockRejectedValue(new Error('network error'));
    render(<MatrixView matrix={makeMatrix()} />);
    fireEvent.click(screen.getByRole('button', { name: /\+ Generate images/i }));
    await waitFor(() => {
      expect(screen.getByText(/network error/i)).toBeInTheDocument();
    });
  });
});

describe('MatrixView — per-cell Regenerate image button', () => {
  it('shows "Regenerate image" button when selected cell has an image', () => {
    const matrix = makeMatrix();
    // Give the off-diagonal cell (0,1) an image
    matrix.cells = matrix.cells.map((c) =>
      c.row === 0 && c.col === 1 ? { ...c, image_url: '/img/cell.jpg' } : c,
    );
    render(<MatrixView matrix={matrix} />);
    // Click the off-diagonal cell to select it
    fireEvent.click(screen.getByText('Concept0x1'));
    expect(screen.getByRole('button', { name: /Regenerate image/i })).toBeInTheDocument();
  });

  it('hides "Regenerate image" button when selected cell has no image', () => {
    render(<MatrixView matrix={makeMatrix()} />);
    fireEvent.click(screen.getByText('Concept0x1'));
    expect(screen.queryByRole('button', { name: /Regenerate image/i })).not.toBeInTheDocument();
  });
});

// ── Description mode detail panel ──────────────────────────────────────────────

describe('MatrixView — description mode detail panel row/col context', () => {
  /**
   * Bug: In description mode, clicking an off-diagonal cell opened a detail
   * panel that looked up getDiagCell(row) and getDiagCell(col) for row/col
   * context. In description mode the (i,i) cells are regular intersection
   * cells whose `label` is the cell's *concept*, not the row label. This
   * produced misleading context (or empty context when (i,i) hadn't been
   * generated yet). The fix reads matrix.row_labels / matrix.col_labels instead.
   */

  function makeDescriptionCell(
    row: number,
    col: number,
    overrides: Partial<MatrixCell> = {},
  ): MatrixCell {
    return {
      id: `cell-${row}-${col}`,
      project_id: 'proj-desc',
      row,
      col,
      label: null,
      definition: null,
      row_descriptor: null,
      col_descriptor: null,
      concept: `Concept${row}x${col}`,
      explanation: `Exp${row}x${col}`,
      image_url: null,
      cell_status: 'complete',
      cell_error: null,
      attempts: 1,
      ...overrides,
    };
  }

  function makeDescriptionMatrix(overrides: Partial<MatrixProject> = {}): MatrixProject {
    const n = 2;
    const cells: MatrixCell[] = [];
    for (let r = 0; r < n; r++) {
      for (let c = 0; c < n; c++) {
        cells.push(makeDescriptionCell(r, c));
      }
    }
    return {
      id: 'proj-desc',
      name: 'Description Matrix',
      theme: 'feels like X but is actually Y',
      n,
      n_rows: 0,
      n_cols: 0,
      row_labels: ['Gen-Z', 'Millennial'],
      col_labels: ['TikTok', 'Instagram'],
      language: 'English',
      style_mode: 'neutral',
      include_images: false,
      input_mode: 'description',
      description: 'feels like one generation but is actually another',
      status: 'complete',
      error_message: null,
      cells,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
      ...overrides,
    };
  }

  it('shows row_labels[row] as Row context when cell is selected in description mode', () => {
    render(<MatrixView matrix={makeDescriptionMatrix()} />);
    // Before clicking: 'Gen-Z' appears once in the row header.
    const beforeCount = screen.queryAllByText('Gen-Z').length;
    // Click cell (0, 1) — row=0 should add 'Gen-Z' in the detail panel Row field.
    fireEvent.click(screen.getByText('Concept0x1'));
    expect(screen.queryAllByText('Gen-Z').length).toBeGreaterThan(beforeCount);
  });

  it('shows col_labels[col] as Col context when cell is selected in description mode', () => {
    render(<MatrixView matrix={makeDescriptionMatrix()} />);
    // Before clicking: 'Instagram' appears once in the col header.
    const beforeCount = screen.queryAllByText('Instagram').length;
    // Click cell (0, 1) — col=1 should add 'Instagram' in the detail panel Col field.
    fireEvent.click(screen.getByText('Concept0x1'));
    expect(screen.queryAllByText('Instagram').length).toBeGreaterThan(beforeCount);
  });

  it('does not add diagonal cell concept as row context in description mode', () => {
    // Give diagonal cell (0,0) a label (mimicking what the stream handler does:
    // label = concept for (i,i) cells in description mode). The old buggy code
    // used getDiagCell(row).label as the Row context, showing the intersection
    // concept instead of the axis label.
    const matrix = makeDescriptionMatrix();
    matrix.cells = matrix.cells.map((c) =>
      c.row === c.col ? { ...c, label: c.concept } : c,
    );
    render(<MatrixView matrix={matrix} />);
    // 'Concept0x0' already appears in the grid cell for (0,0).
    const beforeCount = screen.queryAllByText('Concept0x0').length;
    // After clicking (0,1), the detail panel must NOT add 'Concept0x0' as Row label.
    fireEvent.click(screen.getByText('Concept0x1'));
    expect(screen.queryAllByText('Concept0x0').length).toBe(beforeCount);
  });

  it('shows both Row and Col labels for a cell in a different row/col combination', () => {
    render(<MatrixView matrix={makeDescriptionMatrix()} />);
    const millBefore = screen.queryAllByText('Millennial').length;
    const tikBefore = screen.queryAllByText('TikTok').length;
    // Click cell (1, 0) — row=1 → 'Millennial', col=0 → 'TikTok'
    fireEvent.click(screen.getByText('Concept1x0'));
    expect(screen.queryAllByText('Millennial').length).toBeGreaterThan(millBefore);
    expect(screen.queryAllByText('TikTok').length).toBeGreaterThan(tikBefore);
  });

  it('hides Row label when row_labels is empty (streaming not yet received labels)', () => {
    const matrix = makeDescriptionMatrix({ row_labels: [], col_labels: [] });
    render(<MatrixView matrix={matrix} />);
    fireEvent.click(screen.getByText('Concept0x1'));
    // With empty labels, neither 'Gen-Z' nor 'Instagram' should appear anywhere
    // (the conditional `{rowLabel && ...}` gates the detail panel fields,
    // and the grid headers fall back to 'R0'/'C0' etc.)
    expect(screen.queryByText('Gen-Z')).not.toBeInTheDocument();
    expect(screen.queryByText('Instagram')).not.toBeInTheDocument();
  });
});
