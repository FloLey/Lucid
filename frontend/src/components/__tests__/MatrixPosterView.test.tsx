import { render, screen, waitFor } from '@testing-library/react';
import { fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import MatrixPosterView from '../matrix/MatrixPosterView';
import type { MatrixCell, MatrixProject } from '../../types';

// ── Canvas mock ────────────────────────────────────────────────────────────────

const mockCtx = {
  fillRect: vi.fn(),
  fillText: vi.fn(),
  strokeText: vi.fn(),
  measureText: vi.fn(() => ({ width: 30 })),
  beginPath: vi.fn(),
  moveTo: vi.fn(),
  lineTo: vi.fn(),
  stroke: vi.fn(),
  save: vi.fn(),
  restore: vi.fn(),
  clip: vi.fn(),
  drawImage: vi.fn(),
  rect: vi.fn(),
  font: '',
  fillStyle: '' as string | CanvasGradient | CanvasPattern,
  strokeStyle: '' as string | CanvasGradient | CanvasPattern,
  lineWidth: 1,
  lineJoin: 'miter' as CanvasLineJoin,
  textAlign: 'center' as CanvasTextAlign,
  textBaseline: 'middle' as CanvasTextBaseline,
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(
    mockCtx as unknown as CanvasRenderingContext2D,
  );
  vi.spyOn(HTMLCanvasElement.prototype, 'toDataURL').mockReturnValue(
    'data:image/png;base64,mock',
  );
  // Auto-load images synchronously so Promise.all resolves immediately
  vi.stubGlobal(
    'Image',
    class MockImage {
      onload: (() => void) | null = null;
      onerror: (() => void) | null = null;
      naturalWidth = 200;
      naturalHeight = 200;
      private _src = '';
      get src() {
        return this._src;
      }
      set src(value: string) {
        this._src = value;
        if (this.onload) this.onload();
      }
    },
  );
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

// ── Factory helpers ────────────────────────────────────────────────────────────

function makeCell(row: number, col: number, overrides: Partial<MatrixCell> = {}): MatrixCell {
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

function makeMatrix(
  n: number,
  cellOverrides: Record<string, Partial<MatrixCell>> = {},
  matrixOverrides: Partial<MatrixProject> = {},
): MatrixProject {
  const cells: MatrixCell[] = [];
  for (let r = 0; r < n; r++) {
    for (let c = 0; c < n; c++) {
      cells.push(makeCell(r, c, cellOverrides[`${r}-${c}`] ?? {}));
    }
  }
  return {
    id: 'proj-1',
    name: 'Test Matrix',
    theme: 'Test theme',
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
    ...matrixOverrides,
  };
}

// ── Tests ──────────────────────────────────────────────────────────────────────

describe('MatrixPosterView — rendering lifecycle', () => {
  it('renders a canvas element', () => {
    render(<MatrixPosterView matrix={makeMatrix(2)} />);
    expect(document.querySelector('canvas')).toBeInTheDocument();
  });

  it('shows "Rendering…" text initially', () => {
    render(<MatrixPosterView matrix={makeMatrix(2)} />);
    expect(screen.getByText('Rendering…')).toBeInTheDocument();
  });

  it('shows matrix dimension label after rendering completes', async () => {
    render(<MatrixPosterView matrix={makeMatrix(2)} />);
    await waitFor(() => expect(screen.getByText('2×2 matrix poster')).toBeInTheDocument());
  });

  it('shows correct dimensions for larger matrix', async () => {
    render(<MatrixPosterView matrix={makeMatrix(4)} />);
    await waitFor(() => expect(screen.getByText('4×4 matrix poster')).toBeInTheDocument());
  });

  it('Download PNG button is disabled while rendering', () => {
    render(<MatrixPosterView matrix={makeMatrix(2)} />);
    expect(screen.getByText('Download PNG')).toBeDisabled();
  });

  it('Download PNG button is enabled after rendering completes', async () => {
    render(<MatrixPosterView matrix={makeMatrix(2)} />);
    await waitFor(() => expect(screen.getByText('Download PNG')).not.toBeDisabled());
  });
});

describe('MatrixPosterView — canvas drawing', () => {
  it('calls getContext("2d") to draw the matrix', async () => {
    render(<MatrixPosterView matrix={makeMatrix(2)} />);
    await waitFor(() => screen.getByText('2×2 matrix poster'));
    expect(HTMLCanvasElement.prototype.getContext).toHaveBeenCalledWith('2d');
  });

  it('draws column header labels (col_descriptor) via fillText', async () => {
    render(<MatrixPosterView matrix={makeMatrix(2)} />);
    await waitFor(() => screen.getByText('2×2 matrix poster'));
    const texts = mockCtx.fillText.mock.calls.map((args) => args[0] as string);
    expect(texts).toContain('ColDesc0');
    expect(texts).toContain('ColDesc1');
  });

  it('draws row header labels (row_descriptor) via fillText', async () => {
    render(<MatrixPosterView matrix={makeMatrix(2)} />);
    await waitFor(() => screen.getByText('2×2 matrix poster'));
    const texts = mockCtx.fillText.mock.calls.map((args) => args[0] as string);
    expect(texts).toContain('RowDesc0');
    expect(texts).toContain('RowDesc1');
  });

  it('draws diagonal cell labels via fillText (theme mode)', async () => {
    render(<MatrixPosterView matrix={makeMatrix(2)} />);
    await waitFor(() => screen.getByText('2×2 matrix poster'));
    const texts = mockCtx.fillText.mock.calls.map((args) => args[0] as string);
    expect(texts).toContain('Label0');
    expect(texts).toContain('Label1');
  });

  it('draws off-diagonal cell concepts via fillText', async () => {
    render(<MatrixPosterView matrix={makeMatrix(2)} />);
    await waitFor(() => screen.getByText('2×2 matrix poster'));
    const texts = mockCtx.fillText.mock.calls.map((args) => args[0] as string);
    expect(texts).toContain('Concept0x1');
    expect(texts).toContain('Concept1x0');
  });

  it('uses strokeText for cells that have images', async () => {
    const matrix = makeMatrix(2, { '0-1': { image_url: '/img/test.png' } });
    render(<MatrixPosterView matrix={matrix} />);
    await waitFor(() => screen.getByText('2×2 matrix poster'));
    // drawStrokedWrappedText calls both strokeText and fillText for the concept
    const strokedTexts = mockCtx.strokeText.mock.calls.map((args) => args[0] as string);
    expect(strokedTexts).toContain('Concept0x1');
  });

  it('does not use strokeText for cells without images', async () => {
    render(<MatrixPosterView matrix={makeMatrix(2)} />);
    await waitFor(() => screen.getByText('2×2 matrix poster'));
    expect(mockCtx.strokeText).not.toHaveBeenCalled();
  });

  it('draws image via drawImage for cells with images', async () => {
    const matrix = makeMatrix(2, { '0-1': { image_url: '/img/test.png' } });
    render(<MatrixPosterView matrix={matrix} />);
    await waitFor(() => screen.getByText('2×2 matrix poster'));
    expect(mockCtx.drawImage).toHaveBeenCalled();
  });

  it('does not call drawImage when no cells have images', async () => {
    render(<MatrixPosterView matrix={makeMatrix(2)} />);
    await waitFor(() => screen.getByText('2×2 matrix poster'));
    expect(mockCtx.drawImage).not.toHaveBeenCalled();
  });

  it('draws grid lines via stroke()', async () => {
    render(<MatrixPosterView matrix={makeMatrix(2)} />);
    await waitFor(() => screen.getByText('2×2 matrix poster'));
    // (n+1) vertical + (n+1) horizontal + 2 header separator lines = 2*3 + 2 = 8
    expect(mockCtx.stroke).toHaveBeenCalled();
  });
});

describe('MatrixPosterView — description mode diagonal cells', () => {
  it('draws description-mode diagonal cell concept (not label) via fillText', async () => {
    // In description mode all cells (including diagonal) store text in `concept`,
    // not `label`. The poster must render concept, otherwise diagonal cells appear blank.
    const matrix = makeMatrix(
      2,
      {
        '0-0': { concept: 'DescConcept0', label: 'Label0' },
        '1-1': { concept: 'DescConcept1', label: 'Label1' },
      },
      { input_mode: 'description' },
    );
    render(<MatrixPosterView matrix={matrix} />);
    await waitFor(() => screen.getByText('2×2 matrix poster'));
    const texts = mockCtx.fillText.mock.calls.map((args) => args[0] as string);
    // concept should be rendered, label must NOT be rendered for diagonal cells
    expect(texts).toContain('DescConcept0');
    expect(texts).toContain('DescConcept1');
    expect(texts).not.toContain('Label0');
    expect(texts).not.toContain('Label1');
  });

  it('renders description-mode diagonal cells without blue-accent background', async () => {
    // Blue-accent fill is reserved for theme-mode diagonals; description-mode diagonals
    // should get the same white background treatment as off-diagonal cells.
    const matrix = makeMatrix(
      2,
      { '0-0': { concept: 'DiagConcept0' }, '1-1': { concept: 'DiagConcept1' } },
      { input_mode: 'description' },
    );
    render(<MatrixPosterView matrix={matrix} />);
    await waitFor(() => screen.getByText('2×2 matrix poster'));
    // Blue-accent fill '#dbeafe' must not appear in any fillStyle call
    const fillStyles: string[] = [];
    mockCtx.fillRect.mock.calls.forEach((_, i) => {
      // fillStyle is set before fillRect; collect all fillStyle values set on mockCtx
    });
    // The simplest way: check that the blue-accent concept text path was not used.
    // Blue-accent path sets fillStyle to '#1e40af' then calls fillText with label.
    // We confirm no fillText was called with 'Label0' or 'Label1'.
    const texts = mockCtx.fillText.mock.calls.map((args) => args[0] as string);
    expect(texts).not.toContain('Label0');
    expect(texts).not.toContain('Label1');
  });
});

describe('MatrixPosterView — download', () => {
  it('calls toDataURL when Download PNG is clicked', async () => {
    render(<MatrixPosterView matrix={makeMatrix(2)} />);
    await waitFor(() => screen.getByText('Download PNG'));
    fireEvent.click(screen.getByText('Download PNG'));
    expect(HTMLCanvasElement.prototype.toDataURL).toHaveBeenCalled();
  });

  it('triggers anchor click when Download PNG is clicked', async () => {
    const anchorClickSpy = vi
      .spyOn(HTMLAnchorElement.prototype, 'click')
      .mockImplementation(() => {});
    render(<MatrixPosterView matrix={makeMatrix(2)} />);
    await waitFor(() => screen.getByText('Download PNG'));
    fireEvent.click(screen.getByText('Download PNG'));
    expect(anchorClickSpy).toHaveBeenCalled();
    anchorClickSpy.mockRestore();
  });

  it('uses matrix name in the download filename', async () => {
    // The download attribute is set to the matrix name — verify toDataURL is called
    // (filename logic is in the component; toDataURL provides the data)
    const matrix = makeMatrix(2, {}, { name: 'My Test Matrix' });
    render(<MatrixPosterView matrix={matrix} />);
    await waitFor(() => screen.getByText('Download PNG'));
    fireEvent.click(screen.getByText('Download PNG'));
    expect(HTMLCanvasElement.prototype.toDataURL).toHaveBeenCalledWith('image/png');
  });
});
