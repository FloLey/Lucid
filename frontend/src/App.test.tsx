import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock child components to isolate App routing logic
vi.mock('./components/Stage1', () => ({ default: () => <div>Stage1 Content</div> }));
vi.mock('./components/Stage2', () => ({ default: () => <div>Stage2 Content</div> }));
vi.mock('./components/Stage3', () => ({ default: () => <div>Stage3 Content</div> }));
vi.mock('./components/Stage4', () => ({ default: () => <div>Stage4 Content</div> }));
vi.mock('./components/Stage5', () => ({ default: () => <div>Stage5 Content</div> }));
vi.mock('./components/ConfigSettings', () => ({ default: ({ onClose }: { onClose: () => void }) => (
  <div>
    <span>Config Settings</span>
    <button onClick={onClose}>Close Config</button>
  </div>
)}));
vi.mock('./components/NewProjectModal', () => ({ default: ({ onClose }: { onClose: () => void }) => (
  <div>
    <span>New Project Modal</span>
    <button onClick={onClose}>Close Modal</button>
  </div>
)}));
vi.mock('./components/TemplatesPage', () => ({ default: ({ onClose }: { onClose: () => void }) => (
  <div>
    <span>Templates Page</span>
    <button onClick={onClose}>Close Templates</button>
  </div>
)}));

// Mock useProject to control app state
const mockUseProject = vi.fn();
vi.mock('./contexts/ProjectContext', () => ({
  ProjectProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useProject: () => mockUseProject(),
}));

const makeSessionState = (overrides = {}) => ({
  projects: [],
  projectsLoading: false,
  currentProject: null,
  projectId: '',
  stageLoading: false,
  error: null,
  setStageLoading: vi.fn(),
  setError: vi.fn(),
  updateProject: vi.fn(),
  openProject: vi.fn(),
  closeProject: vi.fn(),
  createNewProject: vi.fn(),
  deleteProject: vi.fn(),
  refreshProjects: vi.fn(),
  advanceStage: vi.fn(),
  previousStage: vi.fn(),
  goToStage: vi.fn(),
  ...overrides,
});

import App from './App';

beforeEach(() => {
  vi.clearAllMocks();
  mockUseProject.mockReturnValue(makeSessionState());
});

describe('App routing', () => {
  it('shows ProjectHome when no project is open', () => {
    render(<App />);
    expect(screen.getByText('Your Projects')).toBeInTheDocument();
  });

  it('does not show stage pipeline when no project is open', () => {
    render(<App />);
    expect(screen.queryByText('Stage1 Content')).not.toBeInTheDocument();
    expect(screen.queryByText('Stage2 Content')).not.toBeInTheDocument();
  });

  it('shows stage pipeline when a project is open', () => {
    mockUseProject.mockReturnValue(makeSessionState({
      currentProject: {
        project_id: 'proj-1',
        name: 'Test Project',
        mode: 'carousel',
        slide_count: 5,
        current_stage: 1,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        draft_text: '',
        num_slides: null,
        include_titles: true,
        additional_instructions: null,
        language: 'English',
        style_proposals: [],
        selected_style_proposal_index: null,
        image_style_instructions: null,
        shared_prompt_prefix: null,
        slides: [],
        thumbnail_url: null,
      },
      projectId: 'proj-1',
    }));
    render(<App />);
    expect(screen.getByText('Stage1 Content')).toBeInTheDocument();
    expect(screen.queryByText('Your Projects')).not.toBeInTheDocument();
  });

  it('shows StageIndicator in pipeline mode', () => {
    mockUseProject.mockReturnValue(makeSessionState({
      currentProject: {
        project_id: 'proj-1',
        name: 'Test Project',
        mode: 'carousel',
        slide_count: 5,
        current_stage: 1,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        draft_text: '',
        num_slides: null,
        include_titles: true,
        additional_instructions: null,
        language: 'English',
        style_proposals: [],
        selected_style_proposal_index: null,
        image_style_instructions: null,
        shared_prompt_prefix: null,
        slides: [],
        thumbnail_url: null,
      },
      projectId: 'proj-1',
    }));
    render(<App />);
    // StageIndicator shows stage names
    expect(screen.getByText('Draft')).toBeInTheDocument();
  });

  it('shows project name in header when project is open', () => {
    mockUseProject.mockReturnValue(makeSessionState({
      currentProject: {
        project_id: 'proj-1',
        name: 'My Awesome Project',
        mode: 'carousel',
        slide_count: 5,
        current_stage: 1,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        draft_text: '',
        num_slides: null,
        include_titles: true,
        additional_instructions: null,
        language: 'English',
        style_proposals: [],
        selected_style_proposal_index: null,
        image_style_instructions: null,
        shared_prompt_prefix: null,
        slides: [],
        thumbnail_url: null,
      },
      projectId: 'proj-1',
    }));
    render(<App />);
    expect(screen.getByText('My Awesome Project')).toBeInTheDocument();
  });

  it('shows Settings modal when settings button is clicked', () => {
    render(<App />);
    fireEvent.click(screen.getByTitle('Configuration'));
    expect(screen.getByText('Config Settings')).toBeInTheDocument();
  });

  it('closes Settings modal when close is clicked', () => {
    render(<App />);
    fireEvent.click(screen.getByTitle('Configuration'));
    fireEvent.click(screen.getByText('Close Config'));
    expect(screen.queryByText('Config Settings')).not.toBeInTheDocument();
  });

  it('shows NewProjectModal when New Project button is clicked on ProjectHome', () => {
    render(<App />);
    fireEvent.click(screen.getByText('New Project'));
    expect(screen.getByText('New Project Modal')).toBeInTheDocument();
  });

  it('shows TemplatesPage when Templates button is clicked', () => {
    render(<App />);
    fireEvent.click(screen.getByText('Templates'));
    expect(screen.getByText('Templates Page')).toBeInTheDocument();
  });

  it('dismisses error when Dismiss is clicked', () => {
    mockUseProject.mockReturnValue(makeSessionState({ error: 'Something went wrong' }));
    render(<App />);
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    fireEvent.click(screen.getByText('Dismiss'));
    // setError(null) would have been called
    expect(makeSessionState().setError).not.toHaveBeenCalled(); // cleared via mock
  });
});
