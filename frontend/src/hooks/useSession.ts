import { useState, useEffect, useCallback } from 'react';
import type { Project, ProjectCard } from '../types';
import * as api from '../services/api';
import { getErrorMessage } from '../utils/error';

/** Ensure array fields are never undefined. */
function normalizeProject(project: Project): Project {
  return {
    ...project,
    slides: project.slides ?? [],
    style_proposals: project.style_proposals ?? [],
  };
}

export function useSession() {
  const [projects, setProjects] = useState<ProjectCard[]>([]);
  const [currentProject, setCurrentProject] = useState<Project | null>(null);
  const [projectsLoading, setProjectsLoading] = useState(true);
  const [stageLoading, setStageLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const setNormalizedProject = useCallback((proj: Project) => {
    setCurrentProject(normalizeProject(proj));
  }, []);

  // Load project list on mount
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

  return {
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
}
