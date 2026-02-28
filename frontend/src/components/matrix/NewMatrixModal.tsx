import { useState } from 'react';
import type { CreateMatrixParams } from '../../services/api';

interface NewMatrixModalProps {
  onClose: () => void;
  onCreate: (params: CreateMatrixParams) => Promise<void>;
}

export default function NewMatrixModal({ onClose, onCreate }: NewMatrixModalProps) {
  const [theme, setTheme] = useState('');
  const [n, setN] = useState(4);
  const [language, setLanguage] = useState('English');
  const [styleMode, setStyleMode] = useState('neutral');
  const [includeImages, setIncludeImages] = useState(false);
  const [name, setName] = useState('');
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCreate = async () => {
    if (!theme.trim()) return;
    setCreating(true);
    setError(null);
    try {
      await onCreate({
        theme: theme.trim(),
        n,
        language,
        style_mode: styleMode,
        include_images: includeImages,
        name: name.trim() || undefined,
      });
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to create matrix');
      setCreating(false);
    }
  };

  const SIZES = [2, 3, 4, 5, 6];
  const STYLE_MODES = ['neutral', 'fun', 'absurd', 'academic'];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl p-6 w-full max-w-md">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">New Concept Matrix</h2>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-500"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 rounded-lg text-sm">
            {error}
          </div>
        )}

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Theme <span className="text-red-500">*</span>
            </label>
            <textarea
              value={theme}
              onChange={(e) => setTheme(e.target.value)}
              placeholder="e.g. The philosophy of time and consciousness"
              rows={3}
              className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-lucid-500 resize-none"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Matrix Size
            </label>
            <div className="flex items-center gap-2">
              {SIZES.map((val) => (
                <button
                  key={val}
                  onClick={() => setN(val)}
                  className={[
                    'w-10 h-10 rounded-lg text-sm font-medium border transition-colors',
                    n === val
                      ? 'bg-lucid-600 text-white border-lucid-600'
                      : 'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 border-gray-300 dark:border-gray-600 hover:border-lucid-400',
                  ].join(' ')}
                >
                  {val}
                </button>
              ))}
              <span className="text-xs text-gray-400 dark:text-gray-500 ml-1">×{n}</span>
            </div>
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
              {n * n} cells total ({n} diagonal + {n * (n - 1)} intersections)
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Language</label>
              <input
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-lucid-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Style</label>
              <select
                value={styleMode}
                onChange={(e) => setStyleMode(e.target.value)}
                className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-lucid-500"
              >
                {STYLE_MODES.map((m) => (
                  <option key={m} value={m}>{m.charAt(0).toUpperCase() + m.slice(1)}</option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Name (optional)
            </label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Auto-generated if left blank"
              className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-lucid-500"
            />
          </div>

          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={includeImages}
              onChange={(e) => setIncludeImages(e.target.checked)}
              className="mt-0.5 w-4 h-4 text-lucid-600 rounded border-gray-300"
            />
            <div>
              <span className="text-sm text-gray-700 dark:text-gray-300">Generate images for each cell</span>
              <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">
                Slower, uses image quota. Can also be triggered later.
              </p>
            </div>
          </label>
        </div>

        <div className="flex justify-end gap-3 mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-600 dark:text-gray-300 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleCreate}
            disabled={!theme.trim() || creating}
            className="px-5 py-2 bg-lucid-600 text-white text-sm font-medium rounded-lg hover:bg-lucid-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {creating ? 'Creating…' : 'Generate Matrix'}
          </button>
        </div>
      </div>
    </div>
  );
}
