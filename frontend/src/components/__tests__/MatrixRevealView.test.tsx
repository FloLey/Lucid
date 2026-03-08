import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import MatrixRevealView from '../matrix/MatrixRevealView';
import type { MatrixCell, MatrixProject } from '../../types';

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

beforeEach(() => {
  vi.clearAllMocks();
});

describe('MatrixRevealView — axis headers', () => {
  it('always shows column axis labels (col_descriptor) without clicking', () => {
    render(<MatrixRevealView matrix={makeMatrix(2)} />);
    expect(screen.getByText('ColDesc0')).toBeInTheDocument();
    expect(screen.getByText('ColDesc1')).toBeInTheDocument();
  });

  it('always shows row axis labels (row_descriptor) without clicking', () => {
    render(<MatrixRevealView matrix={makeMatrix(2)} />);
    expect(screen.getByText('RowDesc0')).toBeInTheDocument();
    expect(screen.getByText('RowDesc1')).toBeInTheDocument();
  });
});

describe('MatrixRevealView — initial hidden state', () => {
  it('all n×n cells start hidden', () => {
    render(<MatrixRevealView matrix={makeMatrix(2)} />);
    expect(screen.getAllByTitle('Tap to reveal')).toHaveLength(4);
  });

  it('no cell label or concept text is visible before any tap', () => {
    render(<MatrixRevealView matrix={makeMatrix(2)} />);
    expect(screen.queryByText('Label0')).not.toBeInTheDocument();
    expect(screen.queryByText('Concept0x1')).not.toBeInTheDocument();
  });
});

describe('MatrixRevealView — diagonal cell reveal cycle', () => {
  it('first tap reveals the label text (name stage)', () => {
    render(<MatrixRevealView matrix={makeMatrix(2)} />);
    fireEvent.click(screen.getAllByTitle('Tap to reveal')[0]); // (0,0)
    expect(screen.getByText('Label0')).toBeInTheDocument();
    expect(screen.getAllByTitle('Tap to reveal')).toHaveLength(3);
  });

  it('second tap reveals the definition text (definition stage)', () => {
    render(<MatrixRevealView matrix={makeMatrix(2)} />);
    fireEvent.click(screen.getAllByTitle('Tap to reveal')[0]);
    fireEvent.click(screen.getByText('Label0'));
    expect(screen.getByText('Def0')).toBeInTheDocument();
    expect(screen.queryByText('Label0')).not.toBeInTheDocument();
  });

  it('third tap hides the cell completely', () => {
    render(<MatrixRevealView matrix={makeMatrix(2)} />);
    fireEvent.click(screen.getAllByTitle('Tap to reveal')[0]);
    fireEvent.click(screen.getByText('Label0'));
    fireEvent.click(screen.getByText('Def0'));
    expect(screen.queryByText('Def0')).not.toBeInTheDocument();
    expect(screen.getAllByTitle('Tap to reveal')).toHaveLength(4);
  });

  it('skips definition stage and hides when definition is null (and no explanation/image)', () => {
    // Diagonal cell with no definition, no explanation, no image → name → hidden
    const matrix = makeMatrix(2, { '0-0': { definition: null } });
    render(<MatrixRevealView matrix={matrix} />);
    fireEvent.click(screen.getAllByTitle('Tap to reveal')[0]);
    expect(screen.getByText('Label0')).toBeInTheDocument();
    fireEvent.click(screen.getByText('Label0'));
    expect(screen.getAllByTitle('Tap to reveal')).toHaveLength(4);
  });

  it('shows explanation after definition when diagonal cell has both', () => {
    const matrix = makeMatrix(2, { '0-0': { explanation: 'DiagExp0' } });
    render(<MatrixRevealView matrix={matrix} />);
    fireEvent.click(screen.getAllByTitle('Tap to reveal')[0]); // name
    fireEvent.click(screen.getByText('Label0'));               // definition
    fireEvent.click(screen.getByText('Def0'));                 // explanation
    expect(screen.getByText('DiagExp0')).toBeInTheDocument();
    expect(screen.queryByText('Def0')).not.toBeInTheDocument();
  });
});

describe('MatrixRevealView — off-diagonal cell reveal cycle (no image)', () => {
  it('first tap reveals concept text (name stage)', () => {
    render(<MatrixRevealView matrix={makeMatrix(2)} />);
    fireEvent.click(screen.getAllByTitle('Tap to reveal')[1]); // (0,1)
    expect(screen.getByText('Concept0x1')).toBeInTheDocument();
  });

  it('second tap reveals explanation text (explanation stage)', () => {
    render(<MatrixRevealView matrix={makeMatrix(2)} />);
    fireEvent.click(screen.getAllByTitle('Tap to reveal')[1]); // name
    fireEvent.click(screen.getByText('Concept0x1'));            // explanation
    expect(screen.getByText('Exp0x1')).toBeInTheDocument();
    expect(screen.queryByText('Concept0x1')).not.toBeInTheDocument();
  });

  it('third tap returns to hidden when there is no image', () => {
    render(<MatrixRevealView matrix={makeMatrix(2)} />);
    fireEvent.click(screen.getAllByTitle('Tap to reveal')[1]);
    fireEvent.click(screen.getByText('Concept0x1'));
    fireEvent.click(screen.getByText('Exp0x1'));
    expect(screen.queryByText('Exp0x1')).not.toBeInTheDocument();
    expect(screen.getAllByTitle('Tap to reveal')).toHaveLength(4);
  });

  it('skips explanation and hides on second tap when explanation is null and no image', () => {
    const matrix = makeMatrix(2, { '0-1': { explanation: null } });
    render(<MatrixRevealView matrix={matrix} />);
    fireEvent.click(screen.getAllByTitle('Tap to reveal')[1]);
    fireEvent.click(screen.getByText('Concept0x1'));
    expect(screen.getAllByTitle('Tap to reveal')).toHaveLength(4);
  });
});

describe('MatrixRevealView — off-diagonal cell with image', () => {
  const makeMatrixWithImage = () =>
    makeMatrix(2, { '0-1': { image_url: '/img/test.png' } });

  it('first tap shows concept (name stage)', () => {
    render(<MatrixRevealView matrix={makeMatrixWithImage()} />);
    fireEvent.click(screen.getAllByTitle('Tap to reveal')[1]);
    expect(screen.getByText('Concept0x1')).toBeInTheDocument();
  });

  it('second tap shows explanation (explanation stage)', () => {
    render(<MatrixRevealView matrix={makeMatrixWithImage()} />);
    fireEvent.click(screen.getAllByTitle('Tap to reveal')[1]);
    fireEvent.click(screen.getByText('Concept0x1'));
    expect(screen.getByText('Exp0x1')).toBeInTheDocument();
  });

  it('third tap shows image with concept overlay (image stage)', () => {
    render(<MatrixRevealView matrix={makeMatrixWithImage()} />);
    fireEvent.click(screen.getAllByTitle('Tap to reveal')[1]); // name
    fireEvent.click(screen.getByText('Concept0x1'));            // explanation
    fireEvent.click(screen.getByText('Exp0x1'));                // image
    const btn = screen.getByText('Concept0x1').closest('button');
    expect(btn).toHaveStyle({ backgroundImage: 'url(/img/test.png)' });
  });

  it('concept text remains visible as overlay in image stage', () => {
    render(<MatrixRevealView matrix={makeMatrixWithImage()} />);
    fireEvent.click(screen.getAllByTitle('Tap to reveal')[1]);
    fireEvent.click(screen.getByText('Concept0x1'));
    fireEvent.click(screen.getByText('Exp0x1'));
    expect(screen.getByText('Concept0x1')).toBeInTheDocument();
  });

  it('fourth tap hides the cell after image stage', () => {
    render(<MatrixRevealView matrix={makeMatrixWithImage()} />);
    fireEvent.click(screen.getAllByTitle('Tap to reveal')[1]);
    fireEvent.click(screen.getByText('Concept0x1'));            // explanation
    fireEvent.click(screen.getByText('Exp0x1'));                // image
    fireEvent.click(screen.getByText('Concept0x1'));            // hidden
    expect(screen.getAllByTitle('Tap to reveal')).toHaveLength(4);
  });

  it('skips explanation and goes directly to image when explanation is null', () => {
    const matrix = makeMatrix(2, { '0-1': { explanation: null, image_url: '/img/test.png' } });
    render(<MatrixRevealView matrix={matrix} />);
    fireEvent.click(screen.getAllByTitle('Tap to reveal')[1]); // name
    fireEvent.click(screen.getByText('Concept0x1'));            // image (no explanation)
    const btn = screen.getByText('Concept0x1').closest('button');
    expect(btn).toHaveStyle({ backgroundImage: 'url(/img/test.png)' });
  });
});

describe('MatrixRevealView — Reveal All / Hide All', () => {
  it('"Reveal all" removes all hidden placeholders', () => {
    render(<MatrixRevealView matrix={makeMatrix(2)} />);
    fireEvent.click(screen.getByText('Reveal all'));
    expect(screen.queryByTitle('Tap to reveal')).not.toBeInTheDocument();
  });

  it('"Reveal all" shows all cell labels and concepts (name stage)', () => {
    render(<MatrixRevealView matrix={makeMatrix(2)} />);
    fireEvent.click(screen.getByText('Reveal all'));
    expect(screen.getByText('Label0')).toBeInTheDocument();
    expect(screen.getByText('Label1')).toBeInTheDocument();
    expect(screen.getByText('Concept0x1')).toBeInTheDocument();
    expect(screen.getByText('Concept1x0')).toBeInTheDocument();
  });

  it('"Hide all" hides all cells after reveal', () => {
    render(<MatrixRevealView matrix={makeMatrix(2)} />);
    fireEvent.click(screen.getByText('Reveal all'));
    fireEvent.click(screen.getByText('Hide all'));
    expect(screen.getAllByTitle('Tap to reveal')).toHaveLength(4);
  });

  it('"Hide all" works even when no cells are revealed', () => {
    render(<MatrixRevealView matrix={makeMatrix(2)} />);
    fireEvent.click(screen.getByText('Hide all'));
    expect(screen.getAllByTitle('Tap to reveal')).toHaveLength(4);
  });
});

describe('MatrixRevealView — multiple independent cells', () => {
  it('revealing one cell does not affect others', () => {
    render(<MatrixRevealView matrix={makeMatrix(2)} />);
    fireEvent.click(screen.getAllByTitle('Tap to reveal')[0]); // reveal (0,0)
    expect(screen.getAllByTitle('Tap to reveal')).toHaveLength(3);
    expect(screen.getByText('Label0')).toBeInTheDocument();
    expect(screen.queryByText('Label1')).not.toBeInTheDocument();
  });

  it('reveals two cells independently', () => {
    render(<MatrixRevealView matrix={makeMatrix(2)} />);
    fireEvent.click(screen.getAllByTitle('Tap to reveal')[0]); // (0,0) → Label0
    fireEvent.click(screen.getAllByTitle('Tap to reveal')[0]); // (0,1) → Concept0x1
    expect(screen.getByText('Label0')).toBeInTheDocument();
    expect(screen.getByText('Concept0x1')).toBeInTheDocument();
    expect(screen.getAllByTitle('Tap to reveal')).toHaveLength(2);
  });
});
