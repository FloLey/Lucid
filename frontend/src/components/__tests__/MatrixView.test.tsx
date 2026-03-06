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
