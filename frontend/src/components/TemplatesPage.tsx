import { useState, useEffect } from 'react';
import type { TemplateData } from '../types';
import * as api from '../services/api';
import { getErrorMessage } from '../utils/error';

interface TemplatesPageProps {
  onClose: () => void;
}

export default function TemplatesPage({ onClose }: TemplatesPageProps) {
  const [templates, setTemplates] = useState<TemplateData[]>([]);
  const [loading, setLoading] = useState(true);
  const [newName, setNewName] = useState('');
  const [creating, setCreating] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      setLoading(true);
      const data = await api.listTemplates();
      setTemplates(data);
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to load templates'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    setError(null);
    try {
      await api.createTemplate(newName.trim());
      setNewName('');
      await load();
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to create template'));
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this template?')) return;
    setDeletingId(id);
    setError(null);
    try {
      await api.deleteTemplate(id);
      await load();
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to delete template'));
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div>
            <h2 className="text-lg font-bold text-gray-900">Templates</h2>
            <p className="text-sm text-gray-500">Reusable project configurations</p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {error && (
            <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm">{error}</div>
          )}

          {loading ? (
            <div className="text-center py-8 text-gray-500">Loading...</div>
          ) : templates.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-gray-500 text-sm">No templates yet.</p>
              <p className="text-gray-400 text-xs mt-1">Create one below to speed up future projects.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {templates.map((t) => (
                <div
                  key={t.id}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-200"
                >
                  <div>
                    <div className="font-medium text-sm text-gray-900">{t.name}</div>
                    <div className="text-xs text-gray-500">{t.default_slide_count} slides \u00b7 {t.default_mode}</div>
                  </div>
                  <button
                    onClick={() => handleDelete(t.id)}
                    disabled={deletingId === t.id}
                    className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                    title="Delete template"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Create new template */}
        <div className="px-6 py-4 border-t border-gray-200">
          <label className="block text-sm font-medium text-gray-700 mb-2">Create new template</label>
          <div className="flex gap-2">
            <input
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleCreate(); }}
              placeholder="Template name"
              className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-lucid-500"
            />
            <button
              onClick={handleCreate}
              disabled={creating || !newName.trim()}
              className="px-4 py-2 text-sm font-medium text-white bg-lucid-600 rounded-lg hover:bg-lucid-700 disabled:opacity-50 transition-colors"
            >
              {creating ? 'Creating...' : 'Create'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
