import { useState, useEffect } from 'react';
import * as api from '../../services/api';
import type { MatrixSettings } from '../../types';

interface MatrixSettingsProps {
  onBack: () => void;
}

export default function MatrixSettingsPage({ onBack }: MatrixSettingsProps) {
  const [settings, setSettings] = useState<MatrixSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api.getMatrixSettings()
      .then(setSettings)
      .catch((e) => setError(e.message ?? 'Failed to load settings'))
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    if (!settings) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await api.updateMatrixSettings(settings);
      setSettings(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    if (!confirm('Reset all matrix settings to defaults?')) return;
    setResetting(true);
    setError(null);
    try {
      const defaults = await api.resetMatrixSettings();
      setSettings(defaults);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to reset');
    } finally {
      setResetting(false);
    }
  };

  const set = <K extends keyof MatrixSettings>(key: K, value: MatrixSettings[K]) => {
    setSettings((prev) => prev ? { ...prev, [key]: value } : prev);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <svg className="w-6 h-6 text-lucid-500 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      </div>
    );
  }

  return (
    <div className="px-6 py-8 max-w-2xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3 mb-8">
        <button
          onClick={onBack}
          className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 transition-colors"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <div>
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">Matrix Settings</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">Configure models and generation parameters.</p>
        </div>
      </div>

      {error && (
        <div className="mb-5 p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 rounded-lg text-sm">
          {error}
        </div>
      )}

      {settings && (
        <div className="space-y-6">
          {/* Models */}
          <section className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">Models</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Text Model
                </label>
                <input
                  value={settings.text_model}
                  onChange={(e) => set('text_model', e.target.value)}
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-lucid-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Image Model
                </label>
                <input
                  value={settings.image_model}
                  onChange={(e) => set('image_model', e.target.value)}
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-lucid-500"
                />
              </div>
            </div>
          </section>

          {/* Temperatures */}
          <section className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">Temperatures</h3>
            <div className="space-y-4">
              {(
                [
                  { key: 'diagonal_temperature', label: 'Diagonal (seed concepts)' },
                  { key: 'axes_temperature', label: 'Axes (descriptors)' },
                  { key: 'cell_temperature', label: 'Cell (off-diagonal)' },
                  { key: 'validation_temperature', label: 'Validation' },
                ] as const
              ).map(({ key, label }) => (
                <div key={key}>
                  <div className="flex items-center justify-between mb-1">
                    <label className="text-sm font-medium text-gray-700 dark:text-gray-300">{label}</label>
                    <span className="text-sm text-gray-500 dark:text-gray-400 tabular-nums">
                      {settings[key].toFixed(2)}
                    </span>
                  </div>
                  <input
                    type="range"
                    min={0}
                    max={2}
                    step={0.05}
                    value={settings[key]}
                    onChange={(e) => set(key, parseFloat(e.target.value))}
                    className="w-full accent-lucid-600"
                  />
                  <div className="flex justify-between text-xs text-gray-400 dark:text-gray-500 mt-0.5">
                    <span>0</span>
                    <span>2</span>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Concurrency & Retries */}
          <section className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">Performance</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Max Concurrency
                </label>
                <input
                  type="number"
                  min={1}
                  max={20}
                  value={settings.max_concurrency}
                  onChange={(e) => set('max_concurrency', parseInt(e.target.value, 10))}
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-lucid-500"
                />
                <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">Parallel LLM calls (1–20)</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Max Retries
                </label>
                <input
                  type="number"
                  min={0}
                  max={5}
                  value={settings.max_retries}
                  onChange={(e) => set('max_retries', parseInt(e.target.value, 10))}
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-lucid-500"
                />
                <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">Failed cell retries (0–5)</p>
              </div>
            </div>
          </section>

          {/* Actions */}
          <div className="flex items-center justify-between">
            <button
              onClick={handleReset}
              disabled={resetting}
              className="px-4 py-2 text-sm text-gray-600 dark:text-gray-300 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 transition-colors"
            >
              {resetting ? 'Resetting…' : 'Reset to defaults'}
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-5 py-2 bg-lucid-600 text-white text-sm font-medium rounded-lg hover:bg-lucid-700 disabled:opacity-50 transition-colors"
            >
              {saved ? 'Saved!' : saving ? 'Saving…' : 'Save settings'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
