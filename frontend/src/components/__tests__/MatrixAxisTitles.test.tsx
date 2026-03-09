import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import MatrixAxisTitles from '../matrix/MatrixAxisTitles';
import type { MatrixProject } from '../../types';

function makeMatrix(overrides: Partial<MatrixProject> = {}): MatrixProject {
  return {
    id: 'proj-1',
    name: 'Test Matrix',
    theme: 'Test theme',
    n: 2,
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
    cells: [],
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    ...overrides,
  };
}

describe('MatrixAxisTitles', () => {
  it('renders nothing in theme mode', () => {
    const { container } = render(
      <MatrixAxisTitles matrix={makeMatrix({ input_mode: 'theme' })} paddingLeft={64} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders nothing in description mode when both axis titles are absent', () => {
    const { container } = render(
      <MatrixAxisTitles
        matrix={makeMatrix({ input_mode: 'description', row_axis_title: undefined, col_axis_title: undefined })}
        paddingLeft={64}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders axis titles in description mode when both are present', () => {
    render(
      <MatrixAxisTitles
        matrix={makeMatrix({ input_mode: 'description', row_axis_title: 'Generation', col_axis_title: 'Platform' })}
        paddingLeft={64}
      />,
    );
    expect(screen.getByText('Generation')).toBeInTheDocument();
    expect(screen.getByText('Platform')).toBeInTheDocument();
    expect(screen.getByText('×')).toBeInTheDocument();
  });

  it('renders when only row_axis_title is set', () => {
    render(
      <MatrixAxisTitles
        matrix={makeMatrix({ input_mode: 'description', row_axis_title: 'Generation', col_axis_title: undefined })}
        paddingLeft={80}
      />,
    );
    expect(screen.getByText('Generation')).toBeInTheDocument();
    expect(screen.queryByText('×')).not.toBeInTheDocument();
  });

  it('renders when only col_axis_title is set', () => {
    render(
      <MatrixAxisTitles
        matrix={makeMatrix({ input_mode: 'description', row_axis_title: undefined, col_axis_title: 'Platform' })}
        paddingLeft={80}
      />,
    );
    expect(screen.getByText('Platform')).toBeInTheDocument();
    expect(screen.queryByText('×')).not.toBeInTheDocument();
  });

  it('applies paddingLeft as inline style', () => {
    const { container } = render(
      <MatrixAxisTitles
        matrix={makeMatrix({ input_mode: 'description', row_axis_title: 'A', col_axis_title: 'B' })}
        paddingLeft={110}
      />,
    );
    const div = container.firstElementChild as HTMLElement;
    expect(div.style.paddingLeft).toBe('110px');
  });
});
