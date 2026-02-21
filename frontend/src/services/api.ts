import axios from 'axios';
import type { Project, ProjectCard, AppConfig, TemplateData, ProjectConfig } from '../types';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Global error interceptor — surfaces user-friendly messages from backend detail field
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail = error.response?.data?.detail;
    if (detail && typeof detail === 'string') {
      error.message = detail;
    }
    return Promise.reject(error);
  },
);

// Project APIs
export const listProjects = async (): Promise<ProjectCard[]> => {
  const response = await api.get('/projects/');
  return response.data.projects;
};

export const createProject = async (templateId?: string): Promise<Project> => {
  const response = await api.post('/projects/', {
    template_id: templateId,
  });
  return response.data.project;
};

export const getProject = async (projectId: string): Promise<Project> => {
  const response = await api.get(`/projects/${projectId}`);
  return response.data.project;
};

export const deleteProject = async (projectId: string): Promise<void> => {
  await api.delete(`/projects/${projectId}`);
};

export const renameProject = async (projectId: string, name: string): Promise<Project> => {
  const response = await api.patch(`/projects/${projectId}/name`, { name });
  return response.data.project;
};

export const advanceStage = async (projectId: string): Promise<Project> => {
  const response = await api.post(`/projects/${projectId}/next-stage`);
  return response.data.project;
};

export const previousStage = async (projectId: string): Promise<Project> => {
  const response = await api.post(`/projects/${projectId}/prev-stage`);
  return response.data.project;
};

export const goToStage = async (projectId: string, stage: number): Promise<Project> => {
  const response = await api.post(`/projects/${projectId}/goto-stage/${stage}`);
  return response.data.project;
};

// Stage Research APIs
export const sendResearchMessage = async (
  projectId: string,
  message: string
): Promise<Project> => {
  const response = await api.post('/stage-research/chat', {
    project_id: projectId,
    message,
  });
  return response.data.project;
};

export const extractDraftFromResearch = async (
  projectId: string,
  researchInstructions?: string
): Promise<Project> => {
  const response = await api.post('/stage-research/extract-draft', {
    project_id: projectId,
    research_instructions: researchInstructions,
  });
  return response.data.project;
};

// Stage Draft APIs
export const generateSlideTexts = async (
  projectId: string,
  draftText: string,
  numSlides?: number,
  includeTitles?: boolean,
  additionalInstructions?: string,
  language: string = 'English',
  wordsPerSlide?: string
): Promise<Project> => {
  const response = await api.post('/stage-draft/generate', {
    project_id: projectId,
    draft_text: draftText,
    num_slides: numSlides,
    include_titles: includeTitles,
    additional_instructions: additionalInstructions,
    language,
    words_per_slide: wordsPerSlide,
  });
  return response.data.project;
};

export const regenerateSlideText = async (
  projectId: string,
  slideIndex: number,
  instruction?: string
): Promise<Project> => {
  const response = await api.post('/stage-draft/regenerate', {
    project_id: projectId,
    slide_index: slideIndex,
    instruction,
  });
  return response.data.project;
};

export const updateSlideText = async (
  projectId: string,
  slideIndex: number,
  title?: string,
  body?: string
): Promise<Project> => {
  const response = await api.post('/stage-draft/update', {
    project_id: projectId,
    slide_index: slideIndex,
    title,
    body,
  });
  return response.data.project;
};

// Stage Style APIs
export const generateStyleProposals = async (
  projectId: string,
  numProposals: number = 3,
  additionalInstructions?: string
): Promise<Project> => {
  const response = await api.post('/stage-style/generate', {
    project_id: projectId,
    num_proposals: numProposals,
    additional_instructions: additionalInstructions,
  });
  return response.data.project;
};

export const selectStyleProposal = async (
  projectId: string,
  proposalIndex: number
): Promise<Project> => {
  const response = await api.post('/stage-style/select', {
    project_id: projectId,
    proposal_index: proposalIndex,
  });
  return response.data.project;
};

// Stage Prompts APIs
export const generatePrompts = async (
  projectId: string,
  styleInstructions?: string
): Promise<Project> => {
  const response = await api.post('/stage-prompts/generate', {
    project_id: projectId,
    image_style_instructions: styleInstructions,
  });
  return response.data.project;
};

export const regeneratePrompt = async (
  projectId: string,
  slideIndex: number,
  instruction?: string
): Promise<Project> => {
  const response = await api.post('/stage-prompts/regenerate', {
    project_id: projectId,
    slide_index: slideIndex,
    instruction,
  });
  return response.data.project;
};

export const updatePrompt = async (
  projectId: string,
  slideIndex: number,
  prompt: string
): Promise<Project> => {
  const response = await api.post('/stage-prompts/update', {
    project_id: projectId,
    slide_index: slideIndex,
    prompt,
  });
  return response.data.project;
};

// Stage Images APIs
export const generateImages = async (projectId: string): Promise<Project> => {
  const response = await api.post('/stage-images/generate', { project_id: projectId });
  return response.data.project;
};

export const regenerateImage = async (
  projectId: string,
  slideIndex: number
): Promise<Project> => {
  const response = await api.post('/stage-images/regenerate', {
    project_id: projectId,
    slide_index: slideIndex,
  });
  return response.data.project;
};

// Stage Typography APIs
export const applyTextToAll = async (projectId: string): Promise<Project> => {
  const response = await api.post('/stage-typography/apply-all', { project_id: projectId });
  return response.data.project;
};

export const applyTextToSlide = async (
  projectId: string,
  slideIndex: number
): Promise<Project> => {
  const response = await api.post('/stage-typography/apply', {
    project_id: projectId,
    slide_index: slideIndex,
  });
  return response.data.project;
};

export const updateStyle = async (
  projectId: string,
  slideIndex: number,
  style: Record<string, unknown>
): Promise<Project> => {
  const response = await api.post('/stage-typography/update-style', {
    project_id: projectId,
    slide_index: slideIndex,
    style,
  });
  return response.data.project;
};

export const applyStyleToAll = async (
  projectId: string,
  style: Record<string, unknown>
): Promise<Project> => {
  const response = await api.post('/stage-typography/apply-style-all', {
    project_id: projectId,
    style,
  });
  return response.data.project;
};

// Export API
export const getExportZipUrl = (projectId: string): string => {
  return `/api/export/zip/${projectId}`;
};

export const getExportSlideUrl = (projectId: string, slideIndex: number): string => {
  return `/api/export/slide/${projectId}/${slideIndex}`;
};

// Config APIs
export const getConfig = async (): Promise<AppConfig> => {
  const response = await api.get('/config');
  return response.data.config;
};

export const updateConfig = async (config: AppConfig): Promise<AppConfig> => {
  const response = await api.put('/config', config);
  return response.data.config;
};

export const updateStageInstructions = async (
  stage: string,
  instructions: string | null
): Promise<AppConfig> => {
  const response = await api.patch('/config/stage-instructions', {
    stage,
    instructions,
  });
  return response.data.config;
};

export const resetConfig = async (): Promise<AppConfig> => {
  const response = await api.post('/config/reset');
  return response.data.config;
};

// Prompts API - edits .prompt files directly
export const getPrompts = async (): Promise<Record<string, string>> => {
  const response = await api.get('/prompts');
  return response.data.prompts;
};

export const updatePrompts = async (prompts: Record<string, string>): Promise<void> => {
  await api.patch('/prompts', { prompts });
};

export interface PromptValidationResponse {
  valid: boolean;
  errors: Record<string, string>;
  warnings: Record<string, string>;
}

export const validatePrompts = async (prompts: Record<string, string>): Promise<PromptValidationResponse> => {
  const response = await api.post('/prompts/validate', { prompts });
  return response.data;
};

// Templates API
export const listTemplates = async (): Promise<TemplateData[]> => {
  const response = await api.get('/templates/');
  return response.data.templates;
};

export const createTemplate = async (
  name: string,
  defaultSlideCount: number = 5
): Promise<TemplateData> => {
  const response = await api.post('/templates/', {
    name,
    default_slide_count: defaultSlideCount,
  });
  return response.data;
};

export const getTemplate = async (templateId: string): Promise<TemplateData> => {
  const response = await api.get(`/templates/${templateId}`);
  return response.data;
};

export const updateTemplate = async (
  templateId: string,
  data: { name?: string; default_slide_count?: number; config?: ProjectConfig }
): Promise<TemplateData> => {
  const response = await api.patch(`/templates/${templateId}`, data);
  return response.data;
};

export const deleteTemplate = async (templateId: string): Promise<void> => {
  await api.delete(`/templates/${templateId}`);
};
