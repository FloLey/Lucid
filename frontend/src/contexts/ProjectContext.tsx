import { useState, useEffect, useCallback, createContext, useContext } from 'react';
import type { ReactNode } from 'react';
import type { Project, ProjectCard } from '../types';
import * as api from '../services/api';
import { getErrorMessage } from '../utils/error';

interface ProjectContextValue {
  projects: ProjectCard[];
  projectsLoading: boolean;
  currentProject: Project | null;
  projectId: string;
  stageLoading: boolean;
  error: string | null;
  setStageLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  updateProject: (project: Project) => void;
  openProject: (projectId: string) => Promise<void>;
  closeProject: () => void;
  createNewProject: (mode?: string, slideCount?: number, templateId?: string) => Promise<void>;
  deleteProject: (projectId: string) => Promise<void>;
  refreshProjects: () => Promise<void>;
  advanceStage: () => Promise<void>;
  previousStage: () => Promise<void>;
  goToStage: (stage: number) => Promise<void>;
}

const ProjectContext = createContext<ProjectContextValue | null>(null);

function normalizeProject(project: Project): Project {
  return {
    ...project,
    slides: project.slides ?? [],
    style_proposals: project.style_proposals ?? [],
  };
}

export function ProjectProvider({ children }: { children: ReactNode }) {
  const [projects, setProjects] = useState<ProjectCard[]>([]);
  const [currentProject, setCurrentProject] = useState<Project | null>(null);
  const [projectsLoading, setProjectsLoading] = useState(true);
  const [stageLoading, setStageLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const setNormalizedProject = useCallback((proj: Project) => {
    setCurrentProject(normalizeProject(proj));
  }, []);

  useEffect(() => {
    const loadProjects = async () => {
      try {
        const cards = await api.listProjects();
        setProjects(cards);
      } catch (err) {
        console.error('Failed to load projects:', err);
      } finally {
        setProjectsLoading(false);
      }
    };
    loadProjects();
  }, []);

  const refreshProjects = useCallback(async () => {
    try {
      const cards = await api.listProjects();
      setProjects(cards);
    } catch (err) {
      console.error('Failed to refresh projects:', err);
    }
  }, []);

  const openProject = useCallback(async (projectId: string) => {
    try {
      const proj = await api.getProject(projectId);
      setNormalizedProject(proj);
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to open project'));
    }
  }, [setNormalizedProject]);

  const closeProject = useCallback(() => {
    setCurrentProject(null);
    refreshProjects();
  }, [refreshProjects]);

  const createNewProject = useCallback(async (
    mode: string = 'carousel',
    slideCount: number = 5,
    templateId?: string
  ) => {
    try {
      const proj = await api.createProject(mode, slideCount, templateId);
      setNormalizedProject(proj);
      await refreshProjects();
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to create project'));
    }
  }, [setNormalizedProject, refreshProjects]);

  const deleteProject = useCallback(async (projectId: string) => {
    try {
      await api.deleteProject(projectId);
      await refreshProjects();
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to delete project'));
    }
  }, [refreshProjects]);

  const updateProject = useCallback((newProject: Project) => {
    setNormalizedProject(newProject);
  }, [setNormalizedProject]);

  const advanceStage = useCallback(async () => {
    if (!currentProject) return;
    try {
      const proj = await api.advanceStage(currentProject.project_id);
      setNormalizedProject(proj);
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to advance stage'));
    }
  }, [currentProject, setNormalizedProject]);

  const previousStage = useCallback(async () => {
    if (!currentProject) return;
    try {
      const proj = await api.previousStage(currentProject.project_id);
      setNormalizedProject(proj);
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to go back'));
    }
  }, [currentProject, setNormalizedProject]);

  const goToStage = useCallback(async (stage: number) => {
    if (!currentProject) return;
    try {
      const proj = await api.goToStage(currentProject.project_id, stage);
      setNormalizedProject(proj);
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to navigate to stage'));
    }
  }, [currentProject, setNormalizedProject]);

  const value: ProjectContextValue = {
    projects,
    projectsLoading,
    currentProject,
    projectId: currentProject?.project_id ?? '',
    stageLoading,
    error,
    setStageLoading,
    setError,
    updateProject,
    openProject,
    closeProject,
    createNewProject,
    deleteProject,
    refreshProjects,
    advanceStage,
    previousStage,
    goToStage,
  };

  return <ProjectContext.Provider value={value}>{children}</ProjectContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useProject(): ProjectContextValue {
  const ctx = useContext(ProjectContext);
  if (!ctx) {
    throw new Error('useProject must be used within a ProjectProvider');
  }
  return ctx;
}
