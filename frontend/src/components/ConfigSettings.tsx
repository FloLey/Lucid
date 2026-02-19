import { useState, useEffect } from 'react';
import type { AppConfig, StageInstructionsConfig, GlobalDefaultsConfig, ImageConfig, StyleConfig } from '../types';
import * as api from '../services/api';
import { getErrorMessage } from '../utils/error';
import Spinner from './Spinner';
import PromptsTab from './config-tabs/PromptsTab';
import InstructionsTab from './config-tabs/InstructionsTab';
import GlobalTab from './config-tabs/GlobalTab';
import ImageTab from './config-tabs/ImageTab';
import StyleTab from './config-tabs/StyleTab';

type Tab = 'prompts' | 'instructions' | 'global' | 'image' | 'style';

const TABS: { id: Tab; label: string }[] = [
  { id: 'prompts', label: 'Prompts' },
  { id: 'instructions', label: 'Instructions' },
  { id: 'global', label: 'Global' },
  { id: 'image', label: 'Image' },
  { id: 'style', label: 'Style' },
];

interface ConfigSettingsProps {
  onClose: () => void;
}

export default function ConfigSettings({ onClose }: ConfigSettingsProps) {
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [prompts, setPrompts] = useState<Record<string, string> | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>('prompts');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [hasValidationErrors, setHasValidationErrors] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [configData, promptsData] = await Promise.all([
        api.getConfig(),
        api.getPrompts()
      ]);
      setConfig(configData);
      setPrompts(promptsData);
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'Failed to load configuration'));
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!config || !prompts) return;

    try {
      setSaving(true);
      setError(null);

      // Save config and prompts in parallel
      await Promise.all([
        api.updateConfig(config),
        api.updatePrompts(prompts)
      ]);

      showSuccess('Configuration saved successfully!');
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'Failed to save configuration'));
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    if (!confirm('Reset configuration to defaults? This will NOT reset prompts (use git to restore those). Continue?')) {
      return;
    }

    try {
      setSaving(true);
      setError(null);
      const data = await api.resetConfig();
      setConfig(data);
      showSuccess('Configuration reset to defaults');
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'Failed to reset configuration'));
    } finally {
      setSaving(false);
    }
  };

  const showSuccess = (message: string) => {
    setSuccessMessage(message);
    setTimeout(() => setSuccessMessage(null), 3000);
  };

  const updatePrompts = (updates: Record<string, string>) => {
    if (!prompts) return;
    setPrompts({ ...prompts, ...updates });
  };

  const updateStageInstructions = (updates: Partial<StageInstructionsConfig>) => {
    if (!config) return;
    setConfig({ ...config, stage_instructions: { ...config.stage_instructions, ...updates } });
  };

  const updateGlobalDefaults = (updates: Partial<GlobalDefaultsConfig>) => {
    if (!config) return;
    setConfig({ ...config, global_defaults: { ...config.global_defaults, ...updates } });
  };

  const updateImageConfig = (updates: Partial<ImageConfig>) => {
    if (!config) return;
    setConfig({ ...config, image: { ...config.image, ...updates } });
  };

  const updateStyleConfig = (updates: Partial<StyleConfig>) => {
    if (!config) return;
    setConfig({ ...config, style: { ...config.style, ...updates } });
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
        <div className="bg-white rounded-xl p-8 shadow-2xl text-center">
          <Spinner size="lg" className="mx-auto" />
          <p className="mt-4 text-gray-600">Loading configuration...</p>
        </div>
      </div>
    );
  }

  if (!config || !prompts) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-5xl w-full h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Configuration</h2>
            <p className="text-sm text-gray-500 mt-1">Customize prompts, defaults, and settings</p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="Close"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-gray-200 px-6">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-lucid-600 text-lucid-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto px-6 py-6">
          {activeTab === 'prompts' && <PromptsTab prompts={prompts} onChange={updatePrompts} onValidationChange={setHasValidationErrors} />}
          {activeTab === 'instructions' && <InstructionsTab config={config} onChange={updateStageInstructions} />}
          {activeTab === 'global' && <GlobalTab config={config} onChange={updateGlobalDefaults} />}
          {activeTab === 'image' && <ImageTab config={config} onChange={updateImageConfig} />}
          {activeTab === 'style' && <StyleTab config={config} onChange={updateStyleConfig} />}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200 bg-gray-50">
          <button
            onClick={handleReset}
            disabled={saving}
            className="px-4 py-2 text-sm font-medium text-red-600 bg-white border border-red-300 rounded-lg hover:bg-red-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Reset All to Defaults
          </button>
          <div className="flex gap-3">
            <button
              onClick={onClose}
              disabled={saving}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving || hasValidationErrors}
              className="px-4 py-2 text-sm font-medium text-white bg-lucid-600 rounded-lg hover:bg-lucid-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
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
                'Save Changes'
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Toast Notifications */}
      {error && (
        <div className="fixed top-4 right-4 bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg shadow-lg max-w-md">
          <div className="flex items-start gap-2">
            <svg className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            <p className="text-sm">{error}</p>
          </div>
        </div>
      )}

      {successMessage && (
        <div className="fixed top-4 right-4 bg-green-50 border border-green-200 text-green-800 px-4 py-3 rounded-lg shadow-lg max-w-md">
          <div className="flex items-start gap-2">
            <svg className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            <p className="text-sm">{successMessage}</p>
          </div>
        </div>
      )}
    </div>
  );
}
