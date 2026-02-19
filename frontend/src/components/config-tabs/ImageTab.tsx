import type { AppConfig, ImageConfig } from '../../types';

interface ImageTabProps {
  config: AppConfig;
  onChange: (updates: Partial<ImageConfig>) => void;
}

export default function ImageTab({ config, onChange }: ImageTabProps) {
  return (
    <div className="space-y-6">
      <p className="text-sm text-gray-600">
        Configure image generation settings.
      </p>

      {/* Width */}
      <div className="space-y-2">
        <label className="text-sm font-semibold text-gray-900">Width (pixels)</label>
        <input
          type="number"
          min="256"
          max="4096"
          value={config.image.width}
          onChange={(e) => onChange({ width: parseInt(e.target.value) })}
          className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-lucid-500 focus:border-lucid-500"
        />
      </div>

      {/* Height */}
      <div className="space-y-2">
        <label className="text-sm font-semibold text-gray-900">Height (pixels)</label>
        <input
          type="number"
          min="256"
          max="4096"
          value={config.image.height}
          onChange={(e) => onChange({ height: parseInt(e.target.value) })}
          className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-lucid-500 focus:border-lucid-500"
        />
      </div>

      {/* Aspect Ratio */}
      <div className="space-y-2">
        <label className="text-sm font-semibold text-gray-900">Aspect Ratio</label>
        <input
          type="text"
          value={config.image.aspect_ratio}
          onChange={(e) => onChange({ aspect_ratio: e.target.value })}
          placeholder="4:5"
          className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-lucid-500 focus:border-lucid-500"
        />
      </div>
    </div>
  );
}
