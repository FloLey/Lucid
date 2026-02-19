import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import NewProjectModal from '../NewProjectModal';

// Mock the api module
vi.mock('../../services/api', () => ({
  listTemplates: vi.fn().mockResolvedValue([]),
}));

const defaultProps = {
  onClose: vi.fn(),
  onCreate: vi.fn().mockResolvedValue(undefined),
};

beforeEach(() => {
  vi.clearAllMocks();
});

/** Render the modal and wait for async effects to settle. */
async function renderModal(props = defaultProps) {
  let result: ReturnType<typeof render>;
  await act(async () => {
    result = render(<NewProjectModal {...props} />);
  });
  return result!;
}

describe('NewProjectModal', () => {
  it('renders the modal heading', async () => {
    await renderModal();
    expect(screen.getByText('New Project')).toBeInTheDocument();
  });

  it('shows format options', async () => {
    await renderModal();
    expect(screen.getByText('Carousel')).toBeInTheDocument();
    expect(screen.getByText('Single Image')).toBeInTheDocument();
  });

  it('shows slide count options when carousel mode is selected', async () => {
    await renderModal();
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByText('7')).toBeInTheDocument();
    expect(screen.getByText('10')).toBeInTheDocument();
  });

  it('hides slide count when single_image mode is selected', async () => {
    await renderModal();
    fireEvent.click(screen.getByText('Single Image'));
    expect(screen.queryByText('Number of slides')).not.toBeInTheDocument();
  });

  it('calls onCreate with default carousel params', async () => {
    const onCreate = vi.fn().mockResolvedValue(undefined);
    await renderModal({ ...defaultProps, onCreate });
    await act(async () => { fireEvent.click(screen.getByText('Create Project')); });
    await waitFor(() => {
      expect(onCreate).toHaveBeenCalledWith('carousel', 5, undefined);
    });
  });

  it('calls onCreate with single_image mode when selected', async () => {
    const onCreate = vi.fn().mockResolvedValue(undefined);
    await renderModal({ ...defaultProps, onCreate });
    fireEvent.click(screen.getByText('Single Image'));
    await act(async () => { fireEvent.click(screen.getByText('Create Project')); });
    await waitFor(() => {
      expect(onCreate).toHaveBeenCalledWith('single_image', 5, undefined);
    });
  });

  it('calls onCreate with selected slide count', async () => {
    const onCreate = vi.fn().mockResolvedValue(undefined);
    await renderModal({ ...defaultProps, onCreate });
    fireEvent.click(screen.getByText('7'));
    await act(async () => { fireEvent.click(screen.getByText('Create Project')); });
    await waitFor(() => {
      expect(onCreate).toHaveBeenCalledWith('carousel', 7, undefined);
    });
  });

  it('calls onClose when Cancel is clicked', async () => {
    const onClose = vi.fn();
    await renderModal({ ...defaultProps, onClose });
    fireEvent.click(screen.getByText('Cancel'));
    expect(onClose).toHaveBeenCalled();
  });

  it('shows template list when templates are available', async () => {
    const { listTemplates } = await import('../../services/api');
    vi.mocked(listTemplates).mockResolvedValueOnce([
      { id: 'tmpl-1', name: 'Marketing', default_mode: 'carousel', default_slide_count: 5, created_at: new Date().toISOString() },
    ]);
    await renderModal();
    await waitFor(() => {
      expect(screen.getByText('Marketing')).toBeInTheDocument();
    });
  });

  it('calls onCreate with selected templateId', async () => {
    const { listTemplates } = await import('../../services/api');
    vi.mocked(listTemplates).mockResolvedValueOnce([
      { id: 'tmpl-1', name: 'Marketing', default_mode: 'carousel', default_slide_count: 5, created_at: new Date().toISOString() },
    ]);
    const onCreate = vi.fn().mockResolvedValue(undefined);
    await renderModal({ ...defaultProps, onCreate });
    await waitFor(() => screen.getByText('Marketing'));
    fireEvent.click(screen.getByText('Marketing'));
    await act(async () => { fireEvent.click(screen.getByText('Create Project')); });
    await waitFor(() => {
      expect(onCreate).toHaveBeenCalledWith('carousel', 5, 'tmpl-1');
    });
  });
});
