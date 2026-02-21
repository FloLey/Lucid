import type { AppConfig, StyleConfig } from '../../types';

interface StyleTabProps {
  config: AppConfig;
  onChange: (updates: Partial<StyleConfig>) => void;
}

export default function StyleTab({ config, onChange }: StyleTabProps) {
  return (
    <div className="space-y-6">
      <p className="text-sm text-gray-600">
        Configure default typography and style settings.
      </p>

      {/* Font Family */}
      <div className="space-y-2">
        <label className="text-sm font-semibold text-gray-900">Font Family</label>
        <input
          type="text"
          value={config.style.default_font_family}
          onChange={(e) => onChange({ default_font_family: e.target.value })}
          placeholder="Inter"
          className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-lucid-500 focus:border-lucid-500"
        />
      </div>

      {/* Font Weight */}
      <div className="space-y-2">
        <label className="text-sm font-semibold text-gray-900">Font Weight</label>
        <input
          type="number"
          min="100"
          max="900"
          step="100"
          value={config.style.default_font_weight}
          onChange={(e) => onChange({ default_font_weight: parseInt(e.target.value) })}
          className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-lucid-500 focus:border-lucid-500"
        />
      </div>

      {/* Font Size */}
      <div className="space-y-2">
        <label className="text-sm font-semibold text-gray-900">Font Size (pixels)</label>
        <input
          type="number"
          min="12"
          max="200"
          value={config.style.default_font_size_px}
          onChange={(e) => onChange({ default_font_size_px: parseInt(e.target.value) })}
          className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-lucid-500 focus:border-lucid-500"
        />
      </div>

      {/* Text Color */}
      <div className="space-y-2">
        <label className="text-sm font-semibold text-gray-900">Text Color</label>
        <div className="flex items-center gap-2">
          <input
            type="color"
            value={config.style.default_text_color}
            onChange={(e) => onChange({ default_text_color: e.target.value })}
            className="w-16 h-10 border border-gray-300 rounded cursor-pointer"
          />
          <input
            type="text"
            value={config.style.default_text_color}
            onChange={(e) => onChange({ default_text_color: e.target.value })}
            placeholder="#FFFFFF"
            className="flex-1 px-3 py-2 text-sm font-mono border border-gray-300 rounded-lg focus:ring-2 focus:ring-lucid-500 focus:border-lucid-500"
          />
        </div>
      </div>

      {/* Alignment */}
      <div className="space-y-2">
        <label className="text-sm font-semibold text-gray-900">Text Alignment</label>
        <select
          value={config.style.default_alignment}
          onChange={(e) => onChange({ default_alignment: e.target.value })}
          className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-lucid-500 focus:border-lucid-500"
        >
          <option value="left">Left</option>
          <option value="center">Center</option>
          <option value="right">Right</option>
        </select>
      </div>

      {/* Text Visibility */}
      <div className="space-y-2">
        <label className="text-sm font-semibold text-gray-900">Text Overlay</label>
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="text-enabled"
            checked={config.style.default_text_enabled ?? true}
            onChange={(e) => onChange({ default_text_enabled: e.target.checked })}
            className="w-4 h-4 text-lucid-600 border-gray-300 rounded focus:ring-lucid-500"
          />
          <label htmlFor="text-enabled" className="text-sm text-gray-700">
            Show text overlay by default
          </label>
        </div>
      </div>

      {/* Stroke/Outline Settings */}
      <div className="pt-4 border-t border-gray-200">
        <h3 className="text-sm font-semibold text-gray-900 mb-4">Text Stroke/Outline</h3>

        {/* Stroke Enabled */}
        <div className="flex items-center gap-2 mb-4">
          <input
            type="checkbox"
            id="stroke-enabled"
            checked={config.style.default_stroke_enabled || false}
            onChange={(e) => onChange({ default_stroke_enabled: e.target.checked })}
            className="w-4 h-4 text-lucid-600 border-gray-300 rounded focus:ring-lucid-500"
          />
          <label htmlFor="stroke-enabled" className="text-sm text-gray-700">
            Enable stroke/outline by default
          </label>
        </div>

        {/* Stroke Width */}
        <div className="space-y-2 mb-4">
          <label className="text-sm font-semibold text-gray-900">Stroke Width (pixels)</label>
          <input
            type="number"
            min="0"
            max="20"
            value={config.style.default_stroke_width_px || 2}
            onChange={(e) => onChange({ default_stroke_width_px: parseInt(e.target.value) })}
            className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-lucid-500 focus:border-lucid-500"
          />
        </div>

        {/* Stroke Color */}
        <div className="space-y-2">
          <label className="text-sm font-semibold text-gray-900">Stroke Color</label>
          <div className="flex items-center gap-2">
            <input
              type="color"
              value={config.style.default_stroke_color || '#000000'}
              onChange={(e) => onChange({ default_stroke_color: e.target.value })}
              className="w-16 h-10 border border-gray-300 rounded cursor-pointer"
            />
            <input
              type="text"
              value={config.style.default_stroke_color || '#000000'}
              onChange={(e) => onChange({ default_stroke_color: e.target.value })}
              placeholder="#000000"
              className="flex-1 px-3 py-2 text-sm font-mono border border-gray-300 rounded-lg focus:ring-2 focus:ring-lucid-500 focus:border-lucid-500"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
