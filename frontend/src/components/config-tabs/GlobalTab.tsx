import type { AppConfig, GlobalDefaultsConfig } from '../../types';

interface GlobalTabProps {
  config: AppConfig;
  onChange: (updates: Partial<GlobalDefaultsConfig>) => void;
}

export default function GlobalTab({ config, onChange }: GlobalTabProps) {
  // Derive checkbox state from config (no local state needed)
  const aiDecides = config.global_defaults.num_slides === null;

  const handleAiDecidesChange = (checked: boolean) => {
    if (checked) {
      onChange({ num_slides: null });
    } else {
      onChange({ num_slides: 5 });
    }
  };

  const handleNumSlidesChange = (value: number) => {
    onChange({ num_slides: value });
  };

  return (
    <div className="space-y-6">
      <p className="text-sm text-gray-600">
        Configure global default parameters used across the application.
      </p>

      {/* Number of Slides */}
      <div className="space-y-3">
        <label className="text-sm font-semibold text-gray-900">Number of Slides</label>
        <p className="text-xs text-gray-500">Default number of slides to generate</p>

        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="ai-decides"
            checked={aiDecides}
            onChange={(e) => handleAiDecidesChange(e.target.checked)}
            className="w-4 h-4 text-lucid-600 border-gray-300 rounded focus:ring-lucid-500"
          />
          <label htmlFor="ai-decides" className="text-sm text-gray-700">
            Let AI decide optimal number (max 10)
          </label>
        </div>

        {!aiDecides && (
          <div className="flex items-center gap-4">
            <input
              type="number"
              min="1"
              max="10"
              value={config.global_defaults.num_slides || 5}
              onChange={(e) => handleNumSlidesChange(parseInt(e.target.value))}
              className="w-24 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-lucid-500 focus:border-lucid-500"
            />
            <span className="text-sm text-gray-500">slides</span>
          </div>
        )}
      </div>

      {/* Language */}
      <div className="space-y-2">
        <label className="text-sm font-semibold text-gray-900">Language</label>
        <p className="text-xs text-gray-500">Default language for generated content</p>
        <input
          type="text"
          value={config.global_defaults.language}
          onChange={(e) => onChange({ language: e.target.value })}
          placeholder="English"
          className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-lucid-500 focus:border-lucid-500"
        />
      </div>

      {/* Include Titles */}
      <div className="space-y-2">
        <label className="text-sm font-semibold text-gray-900">Include Titles</label>
        <p className="text-xs text-gray-500">Generate titles for slides by default</p>
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="include-titles"
            checked={config.global_defaults.include_titles}
            onChange={(e) => onChange({ include_titles: e.target.checked })}
            className="w-4 h-4 text-lucid-600 border-gray-300 rounded focus:ring-lucid-500"
          />
          <label htmlFor="include-titles" className="text-sm text-gray-700">
            Include titles in slides
          </label>
        </div>
      </div>
    </div>
  );
}
