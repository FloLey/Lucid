import type { AppConfig, StageInstructionsConfig } from '../../types';

const STAGE_FIELDS = [
  { key: 'stage1' as keyof StageInstructionsConfig, label: 'Stage 1 (Draft)', description: 'Default instructions for generating slide texts' },
  { key: 'stage_style' as keyof StageInstructionsConfig, label: 'Stage Style', description: 'Default instructions for style proposals' },
  { key: 'stage2' as keyof StageInstructionsConfig, label: 'Stage 2 (Prompts)', description: 'Default instructions for image prompts' },
  { key: 'stage3' as keyof StageInstructionsConfig, label: 'Stage 3 (Images)', description: 'Instructions for image generation (if needed)' },
];

interface InstructionsTabProps {
  config: AppConfig;
  onChange: (updates: Partial<StageInstructionsConfig>) => void;
}

export default function InstructionsTab({ config, onChange }: InstructionsTabProps) {
  return (
    <div className="space-y-6">
      <p className="text-sm text-gray-600">
        Set default additional instructions for each stage. These will be used when no explicit instructions are provided.
        Leave empty to use no default instructions.
      </p>

      {STAGE_FIELDS.map((stage) => (
        <div key={stage.key} className="space-y-2">
          <label className="text-sm font-semibold text-gray-900">{stage.label}</label>
          <p className="text-xs text-gray-500">{stage.description}</p>
          <textarea
            value={config.stage_instructions[stage.key] || ''}
            onChange={(e) => onChange({ [stage.key]: e.target.value || null })}
            placeholder="e.g., Make it funny and engaging..."
            rows={3}
            className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-lucid-500 focus:border-lucid-500 resize-y"
          />
        </div>
      ))}
    </div>
  );
}
