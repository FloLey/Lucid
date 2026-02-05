import axios from 'axios';
import type { Session, ChatResponse } from '../types';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

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

// Stage 1 APIs
export const generateSlideTexts = async (
  sessionId: string,
  draftText: string,
  numSlides: number,
  includeTitles: boolean,
  additionalInstructions?: string
): Promise<Session> => {
  const response = await api.post('/stage1/generate', {
    session_id: sessionId,
    draft_text: draftText,
    num_slides: numSlides,
    include_titles: includeTitles,
    additional_instructions: additionalInstructions,
  });
  return response.data.session;
};

export const regenerateSlideText = async (
  sessionId: string,
  slideIndex: number
): Promise<Session> => {
  const response = await api.post('/stage1/regenerate', {
    session_id: sessionId,
    slide_index: slideIndex,
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

// Stage 2 APIs
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

export const getPresets = async (): Promise<Record<string, unknown>> => {
  const response = await api.get('/stage4/presets');
  return response.data.presets;
};

// Chat API
export const sendChatMessage = async (
  sessionId: string,
  message: string
): Promise<ChatResponse> => {
  const response = await api.post('/chat/message', {
    session_id: sessionId,
    message,
  });
  return response.data;
};

// Export API
export const getExportZipUrl = (sessionId: string): string => {
  return `/api/export/zip/${sessionId}`;
};

export const getExportSlideUrl = (sessionId: string, slideIndex: number): string => {
  return `/api/export/slide/${sessionId}/${slideIndex}`;
};
