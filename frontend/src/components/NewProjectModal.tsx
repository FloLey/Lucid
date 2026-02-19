import { useState, useEffect } from 'react';
import type { TemplateData } from '../types';
import * as api from '../services/api';

interface NewProjectModalProps {
  onClose: () => void;
  onCreate: (mode: string, slideCount: number, templateId?: string) => Promise<void>;
}

const SLIDE_COUNT_OPTIONS = [3, 5, 7, 10];

export default function NewProjectModal({ onClose, onCreate }: NewProjectModalProps) {
  const [mode, setMode] = useState<'carousel' | 'single_image'>('carousel');
  const [slideCount, setSlideCount] = useState(5);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | undefined>(undefined);
  const [templates, setTemplates] = useState<TemplateData[]>([]);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    api.listTemplates().then(setTemplates).catch(console.error);
  }, []);

  const handleCreate = async () => {
    setCreating(true);
    try {
      await onCreate(mode, slideCount, selectedTemplateId);
      onClose();
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-md">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-bold text-gray-900">New Project</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-5 space-y-5">
          {/* Mode */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Format</label>
            <div className="grid grid-cols-2 gap-3">
              {(['carousel', 'single_image'] as const).map((m) => (
                <button
                  key={m}
                  onClick={() => setMode(m)}
                  className={`px-4 py-3 rounded-lg border-2 text-sm font-medium transition-colors text-left ${
                    mode === m
                      ? 'border-lucid-500 bg-lucid-50 text-lucid-700'
                      : 'border-gray-200 text-gray-600 hover:border-gray-300'
                  }`}
                >
                  <div className="font-semibold">
                    {m === 'carousel' ? 'Carousel' : 'Single Image'}
                  </div>
                  <div className="text-xs text-gray-500 mt-0.5">
                    {m === 'carousel' ? 'Multiple slides' : 'One image'}
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Slide count (only for carousel) */}
          {mode === 'carousel' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Number of slides</label>
              <div className="flex gap-2">
                {SLIDE_COUNT_OPTIONS.map((n) => (
                  <button
                    key={n}
                    onClick={() => setSlideCount(n)}
                    className={`flex-1 py-2 rounded-lg text-sm font-medium border transition-colors ${
                      slideCount === n
                        ? 'border-lucid-500 bg-lucid-50 text-lucid-700'
                        : 'border-gray-200 text-gray-600 hover:border-gray-300'
                    }`}
                  >
                    {n}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Template selection */}
          {templates.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Template (optional)</label>
              <div className="space-y-2 max-h-40 overflow-y-auto">
                <button
                  onClick={() => setSelectedTemplateId(undefined)}
                  className={`w-full text-left px-3 py-2 rounded-lg border text-sm transition-colors ${
                    !selectedTemplateId
                      ? 'border-lucid-500 bg-lucid-50 text-lucid-700'
                      : 'border-gray-200 text-gray-600 hover:border-gray-300'
                  }`}
                >
                  No template (blank project)
                </button>
                {templates.map((t) => (
                  <button
                    key={t.id}
                    onClick={() => setSelectedTemplateId(t.id)}
                    className={`w-full text-left px-3 py-2 rounded-lg border text-sm transition-colors ${
                      selectedTemplateId === t.id
                        ? 'border-lucid-500 bg-lucid-50 text-lucid-700'
                        : 'border-gray-200 text-gray-600 hover:border-gray-300'
                    }`}
                  >
                    <div className="font-medium">{t.name}</div>
                    <div className="text-xs text-gray-400">{t.default_slide_count} slides · {t.default_mode}</div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 px-6 py-4 border-t border-gray-200">
          <button
            onClick={onClose}
            disabled={creating}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleCreate}
            disabled={creating}
            className="px-4 py-2 text-sm font-medium text-white bg-lucid-600 rounded-lg hover:bg-lucid-700 disabled:opacity-50 transition-colors"
          >
            {creating ? 'Creating...' : 'Create Project'}
          </button>
        </div>
      </div>
    </div>
  );
}
