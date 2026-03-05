import { render, screen, fireEvent, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import NewMatrixModal from '../matrix/NewMatrixModal';

const defaultProps = {
  onClose: vi.fn(),
  onCreate: vi.fn().mockResolvedValue(undefined),
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe('NewMatrixModal — mode toggle visibility', () => {
  it('renders both Theme and Description mode buttons', () => {
    render(<NewMatrixModal {...defaultProps} />);
    expect(screen.getByRole('button', { name: 'Theme' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Description' })).toBeInTheDocument();
  });

  it('defaults to Theme mode — shows theme textarea', () => {
    render(<NewMatrixModal {...defaultProps} />);
    expect(screen.getByPlaceholderText(/philosophy of time/i)).toBeInTheDocument();
    expect(screen.queryByPlaceholderText(/feels like a certain/i)).not.toBeInTheDocument();
  });

  it('switches to Description input when Description tab is clicked', () => {
    render(<NewMatrixModal {...defaultProps} />);
    fireEvent.click(screen.getByRole('button', { name: 'Description' }));
    expect(screen.getByPlaceholderText(/feels like a certain/i)).toBeInTheDocument();
    expect(screen.queryByPlaceholderText(/philosophy of time/i)).not.toBeInTheDocument();
  });

  it('switches back to Theme input when Theme tab is clicked', () => {
    render(<NewMatrixModal {...defaultProps} />);
    fireEvent.click(screen.getByRole('button', { name: 'Description' }));
    fireEvent.click(screen.getByRole('button', { name: 'Theme' }));
    expect(screen.getByPlaceholderText(/philosophy of time/i)).toBeInTheDocument();
    expect(screen.queryByPlaceholderText(/feels like a certain/i)).not.toBeInTheDocument();
  });
});

describe('NewMatrixModal — validation', () => {
  it('Generate Matrix is disabled when theme input is empty', () => {
    render(<NewMatrixModal {...defaultProps} />);
    expect(screen.getByRole('button', { name: 'Generate Matrix' })).toBeDisabled();
  });

  it('Generate Matrix is disabled when theme has fewer than 3 characters', () => {
    render(<NewMatrixModal {...defaultProps} />);
    fireEvent.change(screen.getByPlaceholderText(/philosophy of time/i), {
      target: { value: 'ab' },
    });
    expect(screen.getByRole('button', { name: 'Generate Matrix' })).toBeDisabled();
  });

  it('Generate Matrix is enabled when theme has 3+ characters', () => {
    render(<NewMatrixModal {...defaultProps} />);
    fireEvent.change(screen.getByPlaceholderText(/philosophy of time/i), {
      target: { value: 'abc' },
    });
    expect(screen.getByRole('button', { name: 'Generate Matrix' })).not.toBeDisabled();
  });

  it('Generate Matrix is disabled when description mode is selected but input is empty', () => {
    render(<NewMatrixModal {...defaultProps} />);
    fireEvent.click(screen.getByRole('button', { name: 'Description' }));
    expect(screen.getByRole('button', { name: 'Generate Matrix' })).toBeDisabled();
  });

  it('Generate Matrix is enabled when description mode has any content', () => {
    render(<NewMatrixModal {...defaultProps} />);
    fireEvent.click(screen.getByRole('button', { name: 'Description' }));
    fireEvent.change(screen.getByPlaceholderText(/feels like a certain/i), {
      target: { value: 'anything' },
    });
    expect(screen.getByRole('button', { name: 'Generate Matrix' })).not.toBeDisabled();
  });
});

describe('NewMatrixModal — submission', () => {
  it('calls onCreate with input_mode:"theme" and theme value', async () => {
    const onCreate = vi.fn().mockResolvedValue(undefined);
    render(<NewMatrixModal {...defaultProps} onCreate={onCreate} />);
    fireEvent.change(screen.getByPlaceholderText(/philosophy of time/i), {
      target: { value: 'Animals of the world' },
    });
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Generate Matrix' }));
    });
    expect(onCreate).toHaveBeenCalledWith(
      expect.objectContaining({ input_mode: 'theme', theme: 'Animals of the world' }),
    );
  });

  it('calls onCreate with input_mode:"description" and description value', async () => {
    const onCreate = vi.fn().mockResolvedValue(undefined);
    render(<NewMatrixModal {...defaultProps} onCreate={onCreate} />);
    fireEvent.click(screen.getByRole('button', { name: 'Description' }));
    fireEvent.change(screen.getByPlaceholderText(/feels like a certain/i), {
      target: { value: 'feels like one era but is actually another' },
    });
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Generate Matrix' }));
    });
    expect(onCreate).toHaveBeenCalledWith(
      expect.objectContaining({
        input_mode: 'description',
        description: 'feels like one era but is actually another',
      }),
    );
  });

  it('trims whitespace from theme before submitting', async () => {
    const onCreate = vi.fn().mockResolvedValue(undefined);
    render(<NewMatrixModal {...defaultProps} onCreate={onCreate} />);
    fireEvent.change(screen.getByPlaceholderText(/philosophy of time/i), {
      target: { value: '  Animals  ' },
    });
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Generate Matrix' }));
    });
    expect(onCreate).toHaveBeenCalledWith(expect.objectContaining({ theme: 'Animals' }));
  });

  it('calls onClose when Cancel is clicked', () => {
    const onClose = vi.fn();
    render(<NewMatrixModal {...defaultProps} onClose={onClose} />);
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(onClose).toHaveBeenCalled();
  });
});

describe('NewMatrixModal — matrix settings', () => {
  it('renders size options 2 through 6', () => {
    render(<NewMatrixModal {...defaultProps} />);
    [2, 3, 4, 5, 6].forEach((n) => {
      expect(screen.getByRole('button', { name: String(n) })).toBeInTheDocument();
    });
  });

  it('defaults to n=4 (shows 16 cells total)', () => {
    render(<NewMatrixModal {...defaultProps} />);
    expect(screen.getByText(/16 cells total/)).toBeInTheDocument();
  });

  it('updates cell count when a different size is selected', () => {
    render(<NewMatrixModal {...defaultProps} />);
    fireEvent.click(screen.getByRole('button', { name: '3' }));
    expect(screen.getByText(/9 cells total/)).toBeInTheDocument();
  });

  it('shows the include images checkbox', () => {
    render(<NewMatrixModal {...defaultProps} />);
    expect(screen.getByText(/generate images for each cell/i)).toBeInTheDocument();
  });

  it('shows the optional name input', () => {
    render(<NewMatrixModal {...defaultProps} />);
    expect(screen.getByPlaceholderText(/auto-generated if left blank/i)).toBeInTheDocument();
  });

  it('includes an optional name in the onCreate params when provided', async () => {
    const onCreate = vi.fn().mockResolvedValue(undefined);
    render(<NewMatrixModal {...defaultProps} onCreate={onCreate} />);
    fireEvent.change(screen.getByPlaceholderText(/philosophy of time/i), {
      target: { value: 'My theme' },
    });
    fireEvent.change(screen.getByPlaceholderText(/auto-generated if left blank/i), {
      target: { value: 'My custom name' },
    });
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Generate Matrix' }));
    });
    expect(onCreate).toHaveBeenCalledWith(
      expect.objectContaining({ name: 'My custom name' }),
    );
  });
});
