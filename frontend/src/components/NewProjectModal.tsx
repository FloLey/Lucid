import { useState, useEffect } from 'react';
import type { TemplateData } from '../types';
import * as api from '../services/api';

interface NewProjectModalProps {
  onClose: () => void;
  onCreate: (templateId?: string) => Promise<void>;
}

export default function NewProjectModal({ onClose, onCreate }: NewProjectModalProps) {
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | undefined>(undefined);
  const [templates, setTemplates] = useState<TemplateData[]>([]);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    api.listTemplates().then(setTemplates).catch(console.error);
  }, []);

  const handleCreate = async () => {
    setCreating(true);
    try {
      await onCreate(selectedTemplateId);
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
        <div className="px-6 py-5">
          <label className="block text-sm font-medium text-gray-700 mb-3">Choose a template</label>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {/* Blank project option */}
            <button
              onClick={() => setSelectedTemplateId(undefined)}
              className={`w-full text-left px-4 py-3 rounded-lg border-2 text-sm transition-colors ${
                !selectedTemplateId
                  ? 'border-lucid-500 bg-lucid-50 text-lucid-700'
                  : 'border-gray-200 text-gray-600 hover:border-gray-300'
              }`}
            >
              <div className="font-medium">Blank project</div>
              <div className="text-xs text-gray-400 mt-0.5">5 slides · no template</div>
            </button>

            {templates.map((t) => (
              <button
                key={t.id}
                onClick={() => setSelectedTemplateId(t.id)}
                className={`w-full text-left px-4 py-3 rounded-lg border-2 text-sm transition-colors ${
                  selectedTemplateId === t.id
                    ? 'border-lucid-500 bg-lucid-50 text-lucid-700'
                    : 'border-gray-200 text-gray-600 hover:border-gray-300'
                }`}
              >
                <div className="font-medium">{t.name}</div>
                <div className="text-xs text-gray-400 mt-0.5">{t.default_slide_count} slides</div>
              </button>
            ))}
          </div>
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
