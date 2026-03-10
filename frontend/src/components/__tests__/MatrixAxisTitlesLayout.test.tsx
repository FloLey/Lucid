import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import MatrixRevealView from '../matrix/MatrixRevealView';
import type { MatrixProject } from '../../types';

// MatrixRevealView uses useMatrixStream indirectly through context — but doesn't;
// it just renders. We do need to mock useMatrix if imported, but MatrixRevealView
// doesn't import it. Safe to render standalone.

function makeMatrix(overrides: Partial<MatrixProject> = {}): MatrixProject {
  return {
    id: 'proj-1',
    name: 'Test Matrix',
    theme: 'Test theme',
    n: 2,
    n_rows: 2,
    n_cols: 3,
    row_labels: ['Row A', 'Row B'],
    col_labels: ['Col X', 'Col Y', 'Col Z'],
    language: 'English',
    style_mode: 'neutral',
    include_images: false,
    input_mode: 'description',
    description: 'a test description',
    status: 'complete',
    error_message: null,
    cells: [],
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('Matrix axis titles layout (reveal view)', () => {
  it('renders row_axis_title as vertical rotated text in description mode', () => {
    render(
      <MatrixRevealView
        matrix={makeMatrix({ row_axis_title: 'Generation', col_axis_title: undefined })}
      />,
    );
    const el = screen.getByText('Generation');
    expect(el).toBeInTheDocument();
    // The element or one of its ancestors should have writingMode style
    const styled = el.closest('[style*="vertical-rl"]');
    expect(styled).not.toBeNull();
  });

  it('renders col_axis_title as horizontal text in description mode', () => {
    render(
      <MatrixRevealView
        matrix={makeMatrix({ row_axis_title: undefined, col_axis_title: 'Platform' })}
      />,
    );
    const el = screen.getByText('Platform');
    expect(el).toBeInTheDocument();
    // Col axis title should NOT have vertical writing mode
    expect(el.style.writingMode ?? '').not.toContain('vertical');
    const parent = el.parentElement as HTMLElement | null;
    if (parent) {
      expect(parent.style.writingMode ?? '').not.toContain('vertical');
    }
  });

  it('renders both titles in description mode when both are present', () => {
    render(
      <MatrixRevealView
        matrix={makeMatrix({ row_axis_title: 'Generation', col_axis_title: 'Platform' })}
      />,
    );
    expect(screen.getByText('Generation')).toBeInTheDocument();
    expect(screen.getByText('Platform')).toBeInTheDocument();
  });

  it('renders no axis titles in theme mode', () => {
    render(
      <MatrixRevealView
        matrix={makeMatrix({
          input_mode: 'theme',
          row_axis_title: 'Generation',
          col_axis_title: 'Platform',
          n_rows: 0,
          n_cols: 0,
          row_labels: [],
          col_labels: [],
        })}
      />,
    );
    expect(screen.queryByText('Generation')).not.toBeInTheDocument();
    expect(screen.queryByText('Platform')).not.toBeInTheDocument();
  });

  it('renders only row title when col title is absent', () => {
    render(
      <MatrixRevealView
        matrix={makeMatrix({ row_axis_title: 'Generation', col_axis_title: undefined })}
      />,
    );
    expect(screen.getByText('Generation')).toBeInTheDocument();
    expect(screen.queryByText('Platform')).not.toBeInTheDocument();
  });

  it('renders only col title when row title is absent', () => {
    render(
      <MatrixRevealView
        matrix={makeMatrix({ row_axis_title: undefined, col_axis_title: 'Platform' })}
      />,
    );
    expect(screen.getByText('Platform')).toBeInTheDocument();
    expect(screen.queryByText('Generation')).not.toBeInTheDocument();
  });

  it('row title element has vertical writing-mode style', () => {
    const { container } = render(
      <MatrixRevealView
        matrix={makeMatrix({ row_axis_title: 'Generation', col_axis_title: undefined })}
      />,
    );
    // Find element with writing-mode set
    const verticalEl = container.querySelector('[style*="vertical-rl"]') as HTMLElement | null;
    expect(verticalEl).not.toBeNull();
    expect(verticalEl?.textContent).toBe('Generation');
  });

  it('col title element has paddingLeft matching the row header width', () => {
    const { container } = render(
      <MatrixRevealView
        matrix={makeMatrix({ row_axis_title: undefined, col_axis_title: 'Platform' })}
      />,
    );
    const el = screen.getByText('Platform');
    // The col title div should have paddingLeft equal to ROW_HEADER_W (80px for reveal view)
    const styledEl = el.closest('[style]') as HTMLElement | null;
    expect(styledEl?.style.paddingLeft).toBe('80px');
    // And should NOT have a vertical writing mode
    expect(styledEl?.style.writingMode ?? '').not.toContain('vertical');
    // Check no ancestor within the component has vertical writing mode on this element's path
    const containers = container.querySelectorAll('[style*="vertical-rl"]');
    let foundInPath = false;
    containers.forEach((node) => {
      if (node.contains(el)) foundInPath = true;
    });
    expect(foundInPath).toBe(false);
  });
});
