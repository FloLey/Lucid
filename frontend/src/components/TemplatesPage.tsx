import { useState, useEffect, useCallback } from 'react';
import type {
  TemplateData,
  ProjectConfig,
  StageInstructionsConfig,
  GlobalDefaultsConfig,
  ImageConfig,
  StyleConfig,
} from '../types';
import * as api from '../services/api';
import { getErrorMessage } from '../utils/error';
import Spinner from './Spinner';
import PromptsTab from './config-tabs/PromptsTab';
import InstructionsTab from './config-tabs/InstructionsTab';
import ImageTab from './config-tabs/ImageTab';
import StyleTab from './config-tabs/StyleTab';

type EditorTab = 'general' | 'style' | 'image' | 'instructions' | 'prompts';

const EDITOR_TABS: { id: EditorTab; label: string }[] = [
  { id: 'general', label: 'General' },
  { id: 'style', label: 'Style' },
  { id: 'image', label: 'Image' },
  { id: 'instructions', label: 'Instructions' },
  { id: 'prompts', label: 'Prompts' },
];

interface TemplatesPageProps {
  onClose: () => void;
}

export default function TemplatesPage({ onClose }: TemplatesPageProps) {
  const [templates, setTemplates] = useState<TemplateData[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [editingConfig, setEditingConfig] = useState<ProjectConfig | null>(null);
  const [editingName, setEditingName] = useState('');
  const [editingSlideCount, setEditingSlideCount] = useState(5);
  const [activeTab, setActiveTab] = useState<EditorTab>('general');
  const [saving, setSaving] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [hasValidationErrors, setHasValidationErrors] = useState(false);

  // New template form
  const [showNewForm, setShowNewForm] = useState(false);
  const [newName, setNewName] = useState('');
  const [newSlideCount, setNewSlideCount] = useState(5);
  const [creating, setCreating] = useState(false);
  // Mobile: 'list' or 'editor'
  const [mobilePanel, setMobilePanel] = useState<'list' | 'editor'>('list');

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const data = await api.listTemplates();
      setTemplates(data);
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to load templates'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const showSuccessMsg = (msg: string) => {
    setSuccess(msg);
    setTimeout(() => setSuccess(null), 3000);
  };

  const handleSelect = (t: TemplateData) => {
    setSelectedId(t.id);
    setEditingConfig(JSON.parse(JSON.stringify(t.config)) as ProjectConfig);
    setEditingName(t.name);
    setEditingSlideCount(t.default_slide_count);
    setActiveTab('general');
    setError(null);
    setHasValidationErrors(false);
    setMobilePanel('editor');
  };

  const handleSave = async () => {
    if (!selectedId || !editingConfig) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await api.updateTemplate(selectedId, {
        name: editingName,
        default_slide_count: editingSlideCount,
        config: editingConfig,
      });
      setTemplates((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
      showSuccessMsg('Template saved!');
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to save template'));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Delete this template? This cannot be undone.')) return;
    setDeletingId(id);
    setError(null);
    try {
      await api.deleteTemplate(id);
      if (selectedId === id) {
        setSelectedId(null);
        setEditingConfig(null);
      }
      await load();
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to delete template'));
    } finally {
      setDeletingId(null);
    }
  };

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    setError(null);
    try {
      const tmpl = await api.createTemplate(newName.trim(), newSlideCount);
      await load();
      setNewName('');
      setNewSlideCount(5);
      setShowNewForm(false);
      handleSelect(tmpl);
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to create template'));
    } finally {
      setCreating(false);
    }
  };

  const updateInstructions = (updates: Partial<StageInstructionsConfig>) => {
    if (!editingConfig) return;
    setEditingConfig({ ...editingConfig, stage_instructions: { ...editingConfig.stage_instructions, ...updates } });
  };
  const updateGlobalDefaults = (updates: Partial<GlobalDefaultsConfig>) => {
    if (!editingConfig) return;
    setEditingConfig({ ...editingConfig, global_defaults: { ...editingConfig.global_defaults, ...updates } });
  };
  const updateImageConfig = (updates: Partial<ImageConfig>) => {
    if (!editingConfig) return;
    setEditingConfig({ ...editingConfig, image: { ...editingConfig.image, ...updates } });
  };
  const updateStyleConfig = (updates: Partial<StyleConfig>) => {
    if (!editingConfig) return;
    setEditingConfig({ ...editingConfig, style: { ...editingConfig.style, ...updates } });
  };
  const updatePrompts = (updates: Record<string, string>) => {
    if (!editingConfig) return;
    setEditingConfig({ ...editingConfig, prompts: { ...editingConfig.prompts, ...updates } });
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-0 sm:p-4">
      <div className="relative bg-white dark:bg-gray-900 rounded-none sm:rounded-xl shadow-2xl w-full max-w-5xl h-full sm:h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-4 sm:px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
          <div className="flex items-center gap-3">
            {/* Mobile back button when in editor panel */}
            {mobilePanel === 'editor' && (
              <button
                onClick={() => setMobilePanel('list')}
                className="sm:hidden p-1 -ml-1 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-white"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
            )}
            <div>
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">Templates</h2>
              <p className="text-sm text-gray-500 dark:text-gray-400 hidden sm:block">Reusable configurations for new projects</p>
            </div>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body: two-panel (stacked on mobile, side-by-side on sm+) */}
        <div className="flex flex-1 min-h-0">
          {/* Left: template list — full width on mobile, fixed 256px on sm+ */}
          <div className={`${mobilePanel === 'editor' ? 'hidden' : 'flex'} sm:flex w-full sm:w-64 flex-shrink-0 sm:border-r border-gray-200 dark:border-gray-700 flex-col`}>
            <div className="flex-1 overflow-y-auto p-3 space-y-1">
              {loading ? (
                <div className="flex justify-center py-8"><Spinner /></div>
              ) : templates.length === 0 ? (
                <div className="text-center py-8 text-sm text-gray-500">No templates yet.</div>
              ) : (
                templates.map((t) => (
                  <div
                    key={t.id}
                    onClick={() => handleSelect(t)}
                    className={`group flex items-center justify-between px-3 py-2.5 rounded-lg cursor-pointer transition-colors ${
                      selectedId === t.id
                        ? 'bg-lucid-50 dark:bg-lucid-900/30 text-lucid-700 dark:text-lucid-300 border border-lucid-200 dark:border-lucid-800'
                        : 'hover:bg-gray-50 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300'
                    }`}
                  >
                    <div className="min-w-0">
                      <div className="font-medium text-sm truncate">{t.name}</div>
                      <div className="text-xs text-gray-400 dark:text-gray-500">{t.default_slide_count} slide{t.default_slide_count !== 1 ? 's' : ''}</div>
                    </div>
                    <button
                      onClick={(e) => handleDelete(t.id, e)}
                      disabled={deletingId === t.id}
                      className="ml-1 p-1 text-gray-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-all flex-shrink-0"
                      title="Delete template"
                    >
                      {deletingId === t.id ? (
                        <Spinner size="sm" />
                      ) : (
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      )}
                    </button>
                  </div>
                ))
              )}
            </div>

            {/* Create new template */}
            <div className="p-3 border-t border-gray-200 dark:border-gray-700 flex-shrink-0">
              {showNewForm ? (
                <div className="space-y-2">
                  <input
                    type="text"
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleCreate();
                      if (e.key === 'Escape') setShowNewForm(false);
                    }}
                    placeholder="Template name"
                    autoFocus
                    className="w-full px-2 py-1.5 text-sm border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-lg focus:outline-none focus:ring-2 focus:ring-lucid-500"
                  />
                  <div className="flex items-center gap-2">
                    <label className="text-xs text-gray-600 flex-shrink-0">Slides:</label>
                    <input
                      type="number"
                      min={1}
                      max={20}
                      value={newSlideCount}
                      onChange={(e) => setNewSlideCount(parseInt(e.target.value) || 5)}
                      className="w-16 px-2 py-1 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-lucid-500"
                    />
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={handleCreate}
                      disabled={creating || !newName.trim()}
                      className="flex-1 py-1.5 text-xs font-medium text-white bg-lucid-600 rounded-lg hover:bg-lucid-700 disabled:opacity-50 transition-colors"
                    >
                      {creating ? 'Creating...' : 'Create'}
                    </button>
                    <button
                      onClick={() => { setShowNewForm(false); setNewName(''); }}
                      className="py-1.5 px-2 text-xs text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <button
                  onClick={() => setShowNewForm(true)}
                  className="w-full py-2 text-sm font-medium text-lucid-600 bg-lucid-50 rounded-lg hover:bg-lucid-100 transition-colors flex items-center justify-center gap-1.5"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  New Template
                </button>
              )}
            </div>
          </div>

          {/* Right: editor — hidden on mobile when list is shown */}
          <div className={`${mobilePanel === 'list' ? 'hidden' : 'flex'} sm:flex flex-1 min-w-0 flex-col`}>
            {!selectedId || !editingConfig ? (
              <div className="flex-1 flex items-center justify-center text-center p-8">
                <div>
                  <div className="w-16 h-16 bg-gray-100 dark:bg-gray-800 rounded-xl flex items-center justify-center mx-auto mb-3">
                    <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                    </svg>
                  </div>
                  <p className="text-gray-500 dark:text-gray-400 text-sm">Select a template to edit, or create a new one.</p>
                </div>
              </div>
            ) : (
              <>
                {/* Tab bar */}
                <div className="flex border-b border-gray-200 dark:border-gray-700 px-4 flex-shrink-0 overflow-x-auto">
                  {EDITOR_TABS.map((tab) => (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={`px-3 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                        activeTab === tab.id
                          ? 'border-lucid-600 text-lucid-600 dark:text-lucid-400'
                          : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:border-gray-300 dark:hover:border-gray-600'
                      }`}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>

                {/* Tab content */}
                <div className="flex-1 overflow-y-auto px-6 py-4">
                  {activeTab === 'general' && (
                    <div className="space-y-5 max-w-md">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Template Name</label>
                        <input
                          type="text"
                          value={editingName}
                          onChange={(e) => setEditingName(e.target.value)}
                          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-lucid-500"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Default Slide Count</label>
                        <p className="text-xs text-gray-500 mb-2">
                          Projects created from this template will start with this many slides.
                        </p>
                        <input
                          type="number"
                          min={1}
                          max={20}
                          value={editingSlideCount}
                          onChange={(e) => setEditingSlideCount(parseInt(e.target.value) || 5)}
                          className="w-24 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-lucid-500"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Default Language</label>
                        <input
                          type="text"
                          value={editingConfig.global_defaults.language}
                          onChange={(e) => updateGlobalDefaults({ language: e.target.value })}
                          className="w-48 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-lucid-500"
                        />
                      </div>
                      <div className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          id="include-titles"
                          checked={editingConfig.global_defaults.include_titles}
                          onChange={(e) => updateGlobalDefaults({ include_titles: e.target.checked })}
                          className="w-4 h-4 text-lucid-600 rounded focus:ring-lucid-500"
                        />
                        <label htmlFor="include-titles" className="text-sm font-medium text-gray-700 dark:text-gray-300 cursor-pointer">
                          Include slide titles by default
                        </label>
                      </div>
                    </div>
                  )}
                  {activeTab === 'style' && (
                    <StyleTab config={editingConfig} onChange={updateStyleConfig} />
                  )}
                  {activeTab === 'image' && (
                    <ImageTab config={editingConfig} onChange={updateImageConfig} />
                  )}
                  {activeTab === 'instructions' && (
                    <InstructionsTab config={editingConfig} onChange={updateInstructions} />
                  )}
                  {activeTab === 'prompts' && (
                    <PromptsTab
                      prompts={editingConfig.prompts}
                      onChange={updatePrompts}
                      onValidationChange={setHasValidationErrors}
                    />
                  )}
                </div>

                {/* Save footer */}
                <div className="flex items-center justify-between px-4 sm:px-6 py-3 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 flex-shrink-0">
                  <p className="text-xs text-gray-500 dark:text-gray-400 hidden sm:block">Changes apply to this template only — not to existing projects.</p>
                  <button
                    onClick={handleSave}
                    disabled={saving || hasValidationErrors}
                    className="px-4 py-2 text-sm font-medium text-white bg-lucid-600 rounded-lg hover:bg-lucid-700 disabled:opacity-50 transition-colors flex items-center gap-2"
                    title={hasValidationErrors ? 'Fix validation errors before saving' : ''}
                  >
                    {saving ? (
                      <>
                        <Spinner size="sm" className="border-white" />
                        Saving...
                      </>
                    ) : hasValidationErrors ? (
                      'Fix Errors to Save'
                    ) : (
                      'Save Template'
                    )}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Toast notifications */}
        {error && (
          <div className="absolute bottom-4 right-4 bg-red-50 dark:bg-red-900/40 border border-red-200 dark:border-red-800 text-red-800 dark:text-red-300 px-4 py-3 rounded-lg shadow-lg max-w-sm text-sm">
            {error}
          </div>
        )}
        {success && (
          <div className="absolute bottom-4 right-4 bg-green-50 dark:bg-green-900/40 border border-green-200 dark:border-green-800 text-green-800 dark:text-green-300 px-4 py-3 rounded-lg shadow-lg max-w-sm text-sm">
            {success}
          </div>
        )}
      </div>
    </div>
  );
}
