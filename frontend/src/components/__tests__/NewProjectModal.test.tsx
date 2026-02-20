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

  it('shows the Blank project option', async () => {
    await renderModal();
    expect(screen.getByText('Blank project')).toBeInTheDocument();
  });

  it('does not show mode toggle (carousel/single image removed)', async () => {
    await renderModal();
    expect(screen.queryByText('Carousel')).not.toBeInTheDocument();
    expect(screen.queryByText('Single Image')).not.toBeInTheDocument();
  });

  it('does not show slide count picker', async () => {
    await renderModal();
    expect(screen.queryByText('Number of slides')).not.toBeInTheDocument();
  });

  it('calls onCreate with undefined when blank project selected', async () => {
    const onCreate = vi.fn().mockResolvedValue(undefined);
    await renderModal({ ...defaultProps, onCreate });
    await act(async () => { fireEvent.click(screen.getByText('Create Project')); });
    await waitFor(() => {
      expect(onCreate).toHaveBeenCalledWith(undefined);
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
      { id: 'tmpl-1', name: 'Marketing', default_slide_count: 5, config: {} as never, created_at: new Date().toISOString() },
    ]);
    await renderModal();
    await waitFor(() => {
      expect(screen.getByText('Marketing')).toBeInTheDocument();
    });
  });

  it('calls onCreate with selected templateId', async () => {
    const { listTemplates } = await import('../../services/api');
    vi.mocked(listTemplates).mockResolvedValueOnce([
      { id: 'tmpl-1', name: 'Marketing', default_slide_count: 5, config: {} as never, created_at: new Date().toISOString() },
    ]);
    const onCreate = vi.fn().mockResolvedValue(undefined);
    await renderModal({ ...defaultProps, onCreate });
    await waitFor(() => screen.getByText('Marketing'));
    fireEvent.click(screen.getByText('Marketing'));
    await act(async () => { fireEvent.click(screen.getByText('Create Project')); });
    await waitFor(() => {
      expect(onCreate).toHaveBeenCalledWith('tmpl-1');
    });
  });

  it('defaults to blank project selection (no template)', async () => {
    const { listTemplates } = await import('../../services/api');
    vi.mocked(listTemplates).mockResolvedValueOnce([
      { id: 'tmpl-1', name: 'Marketing', default_slide_count: 5, config: {} as never, created_at: new Date().toISOString() },
    ]);
    const onCreate = vi.fn().mockResolvedValue(undefined);
    await renderModal({ ...defaultProps, onCreate });
    await waitFor(() => screen.getByText('Marketing'));
    // Don't click on template — keep default blank project
    await act(async () => { fireEvent.click(screen.getByText('Create Project')); });
    await waitFor(() => {
      expect(onCreate).toHaveBeenCalledWith(undefined);
    });
  });
});
