import { useState, useCallback } from 'react';
import * as api from '../services/api';
import { getErrorMessage } from '../utils/error';
import type { ProjectConfig } from '../types';

interface UseTemplateManagerOptions {
  projectConfig: ProjectConfig | undefined;
  slideCount: number;
  onError: (message: string) => void;
}

interface UseTemplateManagerResult {
  showTemplateForm: boolean;
  templateName: string;
  savingTemplate: boolean;
  templateSaved: boolean;
  setTemplateName: (name: string) => void;
  openForm: () => void;
  closeForm: () => void;
  saveTemplate: () => Promise<void>;
}

export function useTemplateManager({
  projectConfig,
  slideCount,
  onError,
}: UseTemplateManagerOptions): UseTemplateManagerResult {
  const [showTemplateForm, setShowTemplateForm] = useState(false);
  const [templateName, setTemplateName] = useState('');
  const [savingTemplate, setSavingTemplate] = useState(false);
  const [templateSaved, setTemplateSaved] = useState(false);

  const openForm = useCallback(() => setShowTemplateForm(true), []);
  const closeForm = useCallback(() => {
    setShowTemplateForm(false);
    setTemplateName('');
  }, []);

  const saveTemplate = useCallback(async () => {
    if (!templateName.trim() || !projectConfig) return;
    setSavingTemplate(true);
    try {
      await api.saveProjectAsTemplate(templateName.trim(), projectConfig, slideCount);
      setTemplateSaved(true);
      setShowTemplateForm(false);
      setTemplateName('');
      setTimeout(() => setTemplateSaved(false), 3000);
    } catch (err) {
      onError(getErrorMessage(err, 'Failed to save template'));
    } finally {
      setSavingTemplate(false);
    }
  }, [templateName, projectConfig, slideCount, onError]);

  return {
    showTemplateForm,
    templateName,
    savingTemplate,
    templateSaved,
    setTemplateName,
    openForm,
    closeForm,
    saveTemplate,
  };
}
