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
    isValidating: false,
    startStream: mockStartStream,
  }),
}));

const mockGenerateMatrixImages = vi.fn();
const mockRevalidateMatrix = vi.fn();
vi.mock('../../services/api', () => ({
  generateMatrixImages: (...args: unknown[]) => mockGenerateMatrixImages(...args),
  revalidateMatrix: (...args: unknown[]) => mockRevalidateMatrix(...args),
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
  mockRevalidateMatrix.mockResolvedValue(undefined);
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

// ── Detail panel — clean name / description / image layout ────────────────────

describe('MatrixView — detail panel shows name and description', () => {
  it('shows diagonal cell label as h3 heading in detail panel when selected', () => {
    render(<MatrixView matrix={makeMatrix()} />);
    // Label0 appears once in grid before click; click opens detail panel
    fireEvent.click(screen.getByText('Label0'));
    // h3 heading is unique to the detail panel (grid uses <p>)
    expect(screen.getByRole('heading', { name: 'Label0' })).toBeInTheDocument();
  });

  it('shows diagonal cell definition text in detail panel', () => {
    render(<MatrixView matrix={makeMatrix()} />);
    // Def0 appears in the grid cell secondary text before click
    const beforeCount = screen.getAllByText('Def0').length;
    fireEvent.click(screen.getByText('Label0'));
    // After click, Def0 also appears in the detail panel — count must increase
    expect(screen.getAllByText('Def0').length).toBeGreaterThan(beforeCount);
  });

  it('shows "About" label only for off-diagonal cells (not in grid)', () => {
    render(<MatrixView matrix={makeMatrix()} />);
    expect(screen.queryByText('About')).not.toBeInTheDocument();
    fireEvent.click(screen.getByText('Concept0x1'));
    expect(screen.getByText('About')).toBeInTheDocument();
  });

  it('shows off-diagonal cell explanation text in detail panel', () => {
    render(<MatrixView matrix={makeMatrix()} />);
    // Exp0x1 appears in the grid cell secondary text before click
    const beforeCount = screen.getAllByText('Exp0x1').length;
    fireEvent.click(screen.getByText('Concept0x1'));
    expect(screen.getAllByText('Exp0x1').length).toBeGreaterThan(beforeCount);
  });

  it('does not show axis row/col context box in the detail panel', () => {
    render(<MatrixView matrix={makeMatrix()} />);
    fireEvent.click(screen.getByText('Concept0x1'));
    // The old axis context box used "Row:" and "Col:" text labels — removed
    expect(screen.queryByText(/^Row:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/^Col:/)).not.toBeInTheDocument();
  });

  it('shows image in detail panel when selected cell has one', () => {
    const matrix = makeMatrix();
    matrix.cells = matrix.cells.map((c) =>
      c.row === 0 && c.col === 1 ? { ...c, image_url: '/img/cell.jpg' } : c,
    );
    const { container } = render(<MatrixView matrix={matrix} />);
    fireEvent.click(screen.getByText('Concept0x1'));
    // Detail panel renders an <img> with the cell's image_url (alt="" → decorative)
    const img = container.querySelector('img[src="/img/cell.jpg"]');
    expect(img).toBeInTheDocument();
  });
});

// ── Re-validate UI ─────────────────────────────────────────────────────────────

describe('MatrixView — Re-validate panel', () => {
  it('shows Re-validate button when matrix is complete and not streaming', () => {
    render(<MatrixView matrix={makeMatrix({ status: 'complete' })} />);
    expect(screen.getByRole('button', { name: /Re-validate/i })).toBeInTheDocument();
  });

  it('hides Re-validate button when matrix is still generating', () => {
    render(<MatrixView matrix={makeMatrix({ status: 'generating' })} />);
    expect(screen.queryByRole('button', { name: /Re-validate/i })).not.toBeInTheDocument();
  });

  it('calls revalidateMatrix and startStream when Re-validate is clicked', async () => {
    render(<MatrixView matrix={makeMatrix({ status: 'complete' })} />);
    fireEvent.click(screen.getByRole('button', { name: /Re-validate/i }));
    await waitFor(() => {
      expect(mockRevalidateMatrix).toHaveBeenCalledWith('proj-1', '');
      expect(mockStartStream).toHaveBeenCalledWith('proj-1');
    });
  });

  it('passes user comment to revalidateMatrix', async () => {
    render(<MatrixView matrix={makeMatrix({ status: 'complete' })} />);
    const textarea = screen.getByPlaceholderText(/Add feedback for re-validation/i);
    fireEvent.change(textarea, { target: { value: 'Only films from the 1980s' } });
    fireEvent.click(screen.getByRole('button', { name: /Re-validate/i }));
    await waitFor(() => {
      expect(mockRevalidateMatrix).toHaveBeenCalledWith('proj-1', 'Only films from the 1980s');
    });
  });

  it('shows error when revalidateMatrix rejects', async () => {
    mockRevalidateMatrix.mockRejectedValue(new Error('server error'));
    render(<MatrixView matrix={makeMatrix({ status: 'complete' })} />);
    fireEvent.click(screen.getByRole('button', { name: /Re-validate/i }));
    await waitFor(() => {
      expect(screen.getByText(/server error/i)).toBeInTheDocument();
    });
  });
});

// ── Mobile layout ──────────────────────────────────────────────────────────────

describe('MatrixView — mobile-responsive layout', () => {
  it('toolbar uses flex-wrap so buttons wrap on small screens', () => {
    const { container } = render(<MatrixView matrix={makeMatrix()} />);
    // The outermost toolbar div must contain flex-wrap
    const toolbar = container.querySelector('.flex-wrap');
    expect(toolbar).toBeInTheDocument();
  });

  it('revalidate panel stacks vertically on mobile (flex-col)', () => {
    const { container } = render(<MatrixView matrix={makeMatrix({ status: 'complete' })} />);
    // The revalidate panel wraps textarea + button; it must have flex-col for mobile stacking
    const panel = container.querySelector('.flex-col');
    expect(panel).toBeInTheDocument();
  });

  it('outer container uses smaller padding on mobile (p-2)', () => {
    const { container } = render(<MatrixView matrix={makeMatrix()} />);
    const outer = container.querySelector('.p-2');
    expect(outer).toBeInTheDocument();
  });

  it('title uses smaller text on mobile (text-base)', () => {
    const { container } = render(<MatrixView matrix={makeMatrix()} />);
    const title = container.querySelector('.text-base');
    expect(title).toBeInTheDocument();
  });
});
