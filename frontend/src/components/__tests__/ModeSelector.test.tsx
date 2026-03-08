import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import ModeSelector from '../ModeSelector';

vi.mock('../../services/api', () => ({
  getInfo: vi.fn().mockResolvedValue(null),
}));

const defaultProps = {
  onSelect: vi.fn(),
  isDark: false,
  onToggleDark: vi.fn(),
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe('ModeSelector', () => {
  it('renders the mode selection heading', () => {
    render(<ModeSelector {...defaultProps} />);
    expect(screen.getByText('What would you like to create?')).toBeInTheDocument();
  });

  it('renders Slide Generation card', () => {
    render(<ModeSelector {...defaultProps} />);
    expect(screen.getByText('Slide Generation')).toBeInTheDocument();
  });

  it('renders Matrix Generation card', () => {
    render(<ModeSelector {...defaultProps} />);
    expect(screen.getByText('Matrix Generation')).toBeInTheDocument();
  });

  it('calls onSelect with "carousel" when Slide Generation is clicked', () => {
    const onSelect = vi.fn();
    render(<ModeSelector {...defaultProps} onSelect={onSelect} />);
    fireEvent.click(screen.getByText('Slide Generation'));
    expect(onSelect).toHaveBeenCalledWith('carousel');
  });

  it('calls onSelect with "matrix" when Matrix Generation is clicked', () => {
    const onSelect = vi.fn();
    render(<ModeSelector {...defaultProps} onSelect={onSelect} />);
    fireEvent.click(screen.getByText('Matrix Generation'));
    expect(onSelect).toHaveBeenCalledWith('matrix');
  });
});
