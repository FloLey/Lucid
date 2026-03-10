import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import DocsModal from '../DocsModal';

const SAMPLE_MARKDOWN = `# Lucid User Guide

---

## Projects

Everything in Lucid lives inside a **project**.

## Templates

A template is a reusable configuration blueprint.

### Built-in templates

Lucid ships with two defaults.
`;

// Stub IntersectionObserver (not implemented in jsdom)
const observeMock = vi.fn();
const disconnectMock = vi.fn();
class IntersectionObserverStub {
  observe = observeMock;
  unobserve = vi.fn();
  disconnect = disconnectMock;
  constructor() {}
}

// Stub Element.prototype.scrollBy / scrollIntoView (not in jsdom)
const scrollByMock = vi.fn();

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ text: () => Promise.resolve(SAMPLE_MARKDOWN) }));
  vi.stubGlobal('IntersectionObserver', IntersectionObserverStub);
  Element.prototype.scrollBy = scrollByMock;
  Element.prototype.scrollIntoView = vi.fn();
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

/** Render and wait until the TOC sidebar ("Contents" label) is visible. */
async function renderModal(onClose = vi.fn()) {
  let result: ReturnType<typeof render>;
  await act(async () => {
    result = render(<DocsModal onClose={onClose} />);
  });
  // Wait for the sidebar "Contents" label — unique, unambiguous
  await waitFor(() => expect(screen.getByText('Contents')).toBeInTheDocument(), { timeout: 5000 });
  return result!;
}

describe('DocsModal', () => {
  it('renders the modal header', async () => {
    await renderModal();
    expect(screen.getByText('Documentation')).toBeInTheDocument();
  });

  it('fetches and renders markdown content', async () => {
    await renderModal();
    // Heading appears in both TOC and content — use getAllByText
    expect(screen.getAllByText('Projects').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Templates').length).toBeGreaterThanOrEqual(1);
  });

  it('renders TOC items for each heading', async () => {
    await renderModal();
    const nav = screen.getByRole('navigation', { name: 'Table of contents' });
    expect(nav.textContent).toContain('Lucid User Guide');
    expect(nav.textContent).toContain('Projects');
    expect(nav.textContent).toContain('Templates');
    expect(nav.textContent).toContain('Built-in templates');
  });

  it('calls scrollBy on the content panel when a TOC item is clicked', async () => {
    await renderModal();
    const nav = screen.getByRole('navigation', { name: 'Table of contents' });
    const projectsButton = Array.from(nav.querySelectorAll('button')).find(
      (b) => b.textContent === 'Projects'
    );
    expect(projectsButton).toBeDefined();
    await act(async () => { fireEvent.click(projectsButton!); });
    expect(scrollByMock).toHaveBeenCalled();
  });

  it('calls onClose when the X button is clicked', async () => {
    const onClose = vi.fn();
    await renderModal(onClose);
    fireEvent.click(screen.getByRole('button', { name: 'Close documentation' }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('calls onClose when the backdrop is clicked', async () => {
    const onClose = vi.fn();
    await renderModal(onClose);
    fireEvent.click(screen.getByRole('dialog'));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('does not close when content panel is clicked', async () => {
    const onClose = vi.fn();
    await renderModal(onClose);
    // Click the inner panel — stopPropagation prevents onClose
    const panel = screen.getByRole('dialog').firstElementChild!;
    fireEvent.click(panel);
    expect(onClose).not.toHaveBeenCalled();
  });

  it('calls onClose when Escape is pressed', async () => {
    const onClose = vi.fn();
    await renderModal(onClose);
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('shows loading state before fetch resolves', async () => {
    let resolve!: (v: string) => void;
    const promise = new Promise<string>((res) => { resolve = res; });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ text: () => promise }));

    await act(async () => { render(<DocsModal onClose={vi.fn()} />); });
    expect(screen.getByText('Loading…')).toBeInTheDocument();

    await act(async () => { resolve(SAMPLE_MARKDOWN); });
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument(), { timeout: 5000 });
  });
});
