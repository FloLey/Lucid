import axios from 'axios';
import type { Session, AppConfig, ChatEvent } from '../types';

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

// Session APIs
export const createSession = async (sessionId: string): Promise<Session> => {
  const response = await api.post('/sessions/create', { session_id: sessionId });
  return response.data.session;
};

export const getSession = async (sessionId: string): Promise<Session> => {
  const response = await api.get(`/sessions/${sessionId}`);
  return response.data.session;
};

export const advanceStage = async (sessionId: string): Promise<Session> => {
  const response = await api.post('/sessions/next-stage', { session_id: sessionId });
  return response.data.session;
};

export const previousStage = async (sessionId: string): Promise<Session> => {
  const response = await api.post('/sessions/previous-stage', { session_id: sessionId });
  return response.data.session;
};

export const goToStage = async (sessionId: string, stage: number): Promise<Session> => {
  const response = await api.post(`/sessions/${sessionId}/stage/${stage}`);
  return response.data.session;
};

// Stage 1 APIs
export const generateSlideTexts = async (
  sessionId: string,
  draftText: string,
  numSlides: number,
  includeTitles: boolean,
  additionalInstructions?: string,
  language: string = 'English'
): Promise<Session> => {
  const response = await api.post('/stage1/generate', {
    session_id: sessionId,
    draft_text: draftText,
    num_slides: numSlides,
    include_titles: includeTitles,
    additional_instructions: additionalInstructions,
    language,
  });
  return response.data.session;
};

export const regenerateSlideText = async (
  sessionId: string,
  slideIndex: number,
  instruction?: string
): Promise<Session> => {
  const response = await api.post('/stage1/regenerate', {
    session_id: sessionId,
    slide_index: slideIndex,
    instruction,
  });
  return response.data.session;
};

export const updateSlideText = async (
  sessionId: string,
  slideIndex: number,
  title?: string,
  body?: string
): Promise<Session> => {
  const response = await api.post('/stage1/update', {
    session_id: sessionId,
    slide_index: slideIndex,
    title,
    body,
  });
  return response.data.session;
};

// Stage Style APIs
export const generateStyleProposals = async (
  sessionId: string,
  numProposals: number = 3,
  additionalInstructions?: string
): Promise<Session> => {
  const response = await api.post('/stage-style/generate', {
    session_id: sessionId,
    num_proposals: numProposals,
    additional_instructions: additionalInstructions,
  });
  return response.data.session;
};

export const selectStyleProposal = async (
  sessionId: string,
  proposalIndex: number
): Promise<Session> => {
  const response = await api.post('/stage-style/select', {
    session_id: sessionId,
    proposal_index: proposalIndex,
  });
  return response.data.session;
};

// Stage 2 APIs (Prompts)
export const generatePrompts = async (
  sessionId: string,
  styleInstructions?: string
): Promise<Session> => {
  const response = await api.post('/stage2/generate', {
    session_id: sessionId,
    image_style_instructions: styleInstructions,
  });
  return response.data.session;
};

export const regeneratePrompt = async (
  sessionId: string,
  slideIndex: number
): Promise<Session> => {
  const response = await api.post('/stage2/regenerate', {
    session_id: sessionId,
    slide_index: slideIndex,
  });
  return response.data.session;
};

export const updatePrompt = async (
  sessionId: string,
  slideIndex: number,
  prompt: string
): Promise<Session> => {
  const response = await api.post('/stage2/update', {
    session_id: sessionId,
    slide_index: slideIndex,
    prompt,
  });
  return response.data.session;
};

// Stage 3 APIs
export const generateImages = async (sessionId: string): Promise<Session> => {
  const response = await api.post('/stage3/generate', { session_id: sessionId });
  return response.data.session;
};

export const regenerateImage = async (
  sessionId: string,
  slideIndex: number
): Promise<Session> => {
  const response = await api.post('/stage3/regenerate', {
    session_id: sessionId,
    slide_index: slideIndex,
  });
  return response.data.session;
};

// Stage 4 APIs
export const applyTextToAll = async (sessionId: string): Promise<Session> => {
  const response = await api.post('/stage4/apply-all', { session_id: sessionId });
  return response.data.session;
};

export const applyTextToSlide = async (
  sessionId: string,
  slideIndex: number
): Promise<Session> => {
  const response = await api.post('/stage4/apply', {
    session_id: sessionId,
    slide_index: slideIndex,
  });
  return response.data.session;
};

export const updateStyle = async (
  sessionId: string,
  slideIndex: number,
  style: Record<string, unknown>
): Promise<Session> => {
  const response = await api.post('/stage4/update-style', {
    session_id: sessionId,
    slide_index: slideIndex,
    style,
  });
  return response.data.session;
};

export const applyStyleToAll = async (
  sessionId: string,
  style: Record<string, unknown>
): Promise<Session> => {
  const response = await api.post('/stage4/apply-style-all', {
    session_id: sessionId,
    style,
  });
  return response.data.session;
};

// Chat API (SSE streaming)
export const sendChatMessageSSE = (
  sessionId: string,
  message: string,
  onEvent: (event: ChatEvent) => void,
  signal?: AbortSignal,
): Promise<void> => {
  return fetch('/api/chat/message', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, message }),
    signal,
  }).then(async (response) => {
    if (!response.ok || !response.body) {
      onEvent({ event: 'error', message: `HTTP ${response.status}` });
      return;
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed.startsWith('data: ')) {
          try {
            const data = JSON.parse(trimmed.slice(6)) as ChatEvent;
            onEvent(data);
          } catch {
            // skip malformed lines
          }
        }
      }
    }
  });
};

export const cancelAgent = async (sessionId: string): Promise<void> => {
  await api.post('/chat/cancel', { session_id: sessionId });
};

export const undoAgent = async (sessionId: string): Promise<Session> => {
  const response = await api.post('/chat/undo', { session_id: sessionId });
  return response.data.session;
};

// Export API
export const getExportZipUrl = (sessionId: string): string => {
  return `/api/export/zip/${sessionId}`;
};

export const getExportSlideUrl = (sessionId: string, slideIndex: number): string => {
  return `/api/export/slide/${sessionId}/${slideIndex}`;
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
