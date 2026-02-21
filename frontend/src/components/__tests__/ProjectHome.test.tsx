import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import ProjectHome from '../ProjectHome';
import type { ProjectCard } from '../../types';

const mockProjects: ProjectCard[] = [
  {
    project_id: 'proj-1',
    name: 'My First Carousel',
    current_stage: 3,
    slide_count: 5,
    thumbnail_url: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    project_id: 'proj-2',
    name: 'Travel Photos',
    current_stage: 5,
    slide_count: 7,
    thumbnail_url: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];

const defaultProps = {
  projects: [],
  loading: false,
  onOpen: vi.fn(),
  onNewProject: vi.fn(),
  onDelete: vi.fn(),
  onTemplates: vi.fn(),
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe('ProjectHome', () => {
  it('renders the page heading', () => {
    render(<ProjectHome {...defaultProps} />);
    expect(screen.getByText('Your Projects')).toBeInTheDocument();
  });

  it('shows empty state when no projects and not loading', () => {
    render(<ProjectHome {...defaultProps} projects={[]} loading={false} />);
    expect(screen.getByText('No projects yet')).toBeInTheDocument();
    expect(screen.getByText('Create your first project')).toBeInTheDocument();
  });

  it('shows loading skeletons when loading', () => {
    render(<ProjectHome {...defaultProps} loading={true} />);
    expect(screen.queryByText('No projects yet')).not.toBeInTheDocument();
    // Loading state renders animated placeholders (no project cards)
    expect(screen.queryByText('My First Carousel')).not.toBeInTheDocument();
  });

  it('renders project cards when projects exist', () => {
    render(<ProjectHome {...defaultProps} projects={mockProjects} />);
    expect(screen.getByText('My First Carousel')).toBeInTheDocument();
    expect(screen.getByText('Travel Photos')).toBeInTheDocument();
  });

  it('shows stage label on project card', () => {
    render(<ProjectHome {...defaultProps} projects={mockProjects} />);
    expect(screen.getByText('Stage 3: Prompts')).toBeInTheDocument();
    expect(screen.getByText('Stage 5: Typography')).toBeInTheDocument();
  });

  it('calls onOpen when a project card is clicked', () => {
    const onOpen = vi.fn();
    render(<ProjectHome {...defaultProps} projects={mockProjects} onOpen={onOpen} />);
    fireEvent.click(screen.getByText('My First Carousel'));
    expect(onOpen).toHaveBeenCalledWith('proj-1');
  });

  it('calls onNewProject when "New Project" button is clicked', () => {
    const onNewProject = vi.fn();
    render(<ProjectHome {...defaultProps} onNewProject={onNewProject} />);
    fireEvent.click(screen.getByText('New Project'));
    expect(onNewProject).toHaveBeenCalled();
  });

  it('calls onNewProject from empty state CTA', () => {
    const onNewProject = vi.fn();
    render(<ProjectHome {...defaultProps} projects={[]} onNewProject={onNewProject} />);
    fireEvent.click(screen.getByText('Create your first project'));
    expect(onNewProject).toHaveBeenCalled();
  });

  it('calls onTemplates when "Templates" button is clicked', () => {
    const onTemplates = vi.fn();
    render(<ProjectHome {...defaultProps} onTemplates={onTemplates} />);
    fireEvent.click(screen.getByText('Templates'));
    expect(onTemplates).toHaveBeenCalled();
  });
});
