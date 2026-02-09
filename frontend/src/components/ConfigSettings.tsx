import { useState, useEffect } from 'react';
import type { AppConfig, StageInstructionsConfig, GlobalDefaultsConfig, ImageConfig, StyleConfig } from '../types';
import * as api from '../services/api';

type Tab = 'prompts' | 'instructions' | 'global' | 'image' | 'style';

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
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load configuration');
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
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save configuration');
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
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to reset configuration');
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
        <div className="bg-white rounded-xl p-8 shadow-2xl">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-lucid-600 mx-auto"></div>
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
          {[
            { id: 'prompts' as Tab, label: 'Prompts', icon: '📝' },
            { id: 'instructions' as Tab, label: 'Instructions', icon: '📋' },
            { id: 'global' as Tab, label: 'Global', icon: '🌍' },
            { id: 'image' as Tab, label: 'Image', icon: '🖼️' },
            { id: 'style' as Tab, label: 'Style', icon: '🎨' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-lucid-600 text-lucid-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <span className="mr-2">{tab.icon}</span>
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
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
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

// Prompts Tab Component
function PromptsTab({ prompts, onChange, onValidationChange }: {
  prompts: Record<string, string>;
  onChange: (updates: Record<string, string>) => void;
  onValidationChange: (hasErrors: boolean) => void;
}) {
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});
  const [validationWarnings, setValidationWarnings] = useState<Record<string, string>>({});
  const [validating, setValidating] = useState(false);

  const promptList = [
    {
      key: 'slide_generation',
      label: 'Slide Generation',
      description: 'Generate slide texts from draft',
      variables: [
        '{num_slides_instruction} → "Generate exactly 5 slides." or "Choose the optimal number of slides based on the content (maximum 10 slides)."',
        '{language_instruction} → "Write ALL slide content in English."',
        '{title_instruction} → "Each slide MUST have both a title and body." or "Each slide should only have body text (no titles)."',
        '{additional_instructions} → User-provided instructions (optional)',
        '{draft} → User\'s original draft text',
        '{slide_format} → \'"title" (string) and "body" (string)\' or \'"body" (string) only\'',
        '{response_format} → \'{"slides": [{"title": "Hook", "body": "Grab attention here"}, ...]}\' or \'{"slides": [{"body": "First slide content"}, ...]}\''
      ]
    },
    {
      key: 'style_proposal',
      label: 'Style Proposal',
      description: 'Generate visual style proposals',
      variables: [
        '{num_proposals} → Number (e.g., 3)',
        '{slides_text} → "Slide 1: Title\\nBody text\\nSlide 2: ..."',
        '{additional_instructions} → "Additional instructions: Make it vibrant" or empty',
        '{response_format} → \'{"proposals": [{"description": "your image generation prompt here"}]}\''
      ]
    },
    {
      key: 'generate_single_image_prompt',
      label: 'Image Prompt Generation (Per-Slide)',
      description: 'Generate image prompts for each slide in parallel',
      variables: [
        '{slide_text} → "Title\\n\\nBody text of the slide"',
        '{shared_theme} → "Soft watercolor washes in muted earth tones, warm lighting..."',
        '{style_instructions_text} → "Style instructions: Modern and minimal" or empty',
        '{context} → "Slide 1: ...\\nSlide 2: ... ← CURRENT SLIDE\\nSlide 3: ..."',
        '{instruction_text} → "Additional instruction for this regeneration: make it darker" or empty',
        '{response_format} → \'{"prompt": "your slide-specific image prompt here"}\''
      ]
    },
    {
      key: 'regenerate_single_slide',
      label: 'Regenerate Single Slide',
      description: 'Regenerate one slide\'s text with full context',
      variables: [
        '{draft_text} → Original user draft text',
        '{language_instruction} → "Write ALL slide content in English."',
        '{all_slides_context} → "Slide 1: ...\\nSlide 2: ... ← CURRENT SLIDE\\nSlide 3: ..."',
        '{current_text} → "Current slide title\\n\\nCurrent slide body"',
        '{instruction_text} → "Additional instruction: Make it more engaging" or empty',
        '{title_instruction} → "Each slide MUST have both a title and body." or "Each slide should only have body text (no titles)."',
        '{response_format} → \'{"title": "New Title", "body": "New body text"}\' or \'{"body": "New body text"}\''
      ]
    },
    {
      key: 'chat_routing',
      label: 'Chat Routing',
      description: 'Route chat commands to tools',
      variables: [
        '{current_stage} → "1" or "2" or "3" or "4" or "5"',
        '{tool_descriptions} → "- auto_generate: Generate all content\\n- regenerate_slide: Regenerate one slide\\n..."',
        '{message} → User\'s chat message',
        '{response_format} → \'{"tool": "tool_name", "params": {}, "response": "A brief response to the user"}\' or \'{"tool": null, "response": "Your helpful response"}\''
      ]
    },
  ];

  // Validate prompts when they change (debounced)
  useEffect(() => {
    const timer = setTimeout(async () => {
      try {
        setValidating(true);
        const result = await api.validatePrompts(prompts);
        setValidationErrors(result.errors);
        setValidationWarnings(result.warnings);
        onValidationChange(Object.keys(result.errors).length > 0);
      } catch (err) {
        console.error('Validation error:', err);
        onValidationChange(false);
      } finally {
        setValidating(false);
      }
    }, 500); // Debounce 500ms

    return () => clearTimeout(timer);
  }, [prompts, onValidationChange]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-sm text-gray-600">
            Edit the AI prompts stored in <code className="px-1.5 py-0.5 bg-gray-100 rounded text-xs font-mono">backend/prompts/*.prompt</code> files. Use <code className="px-1.5 py-0.5 bg-gray-100 rounded text-xs font-mono">&#123;variable&#125;</code> syntax for dynamic values.
          </p>
          {Object.keys(validationErrors).length > 0 && (
            <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-700">
              <strong>Validation errors found:</strong> Fix missing variables before saving.
            </div>
          )}
          <p className="text-xs text-gray-500 mt-2">
            💡 Tip: These files are version-controlled. Use git to restore originals if needed.
          </p>
        </div>
      </div>

      {promptList.map((prompt) => {
        const hasError = validationErrors[prompt.key];
        const hasWarning = validationWarnings[prompt.key];

        return (
          <div key={prompt.key} className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-sm font-semibold text-gray-900">{prompt.label}</label>
              <div className="flex items-center gap-2">
                {validating && (
                  <span className="text-xs text-gray-400">Validating...</span>
                )}
                {hasError && (
                  <span className="text-xs text-red-600 font-medium">❌ Invalid</span>
                )}
                {!hasError && hasWarning && (
                  <span className="text-xs text-yellow-600 font-medium">⚠️ Warning</span>
                )}
                {!hasError && !hasWarning && !validating && (
                  <span className="text-xs text-green-600 font-medium">✓ Valid</span>
                )}
                <span className="text-xs text-gray-500">
                  {prompts[prompt.key]?.length || 0} characters
                </span>
              </div>
            </div>
            <p className="text-xs text-gray-500">{prompt.description}</p>
            <textarea
              value={prompts[prompt.key] || ''}
              onChange={(e) => onChange({ [prompt.key]: e.target.value })}
              rows={8}
              className={`w-full px-3 py-2 text-sm font-mono border rounded-lg focus:ring-2 resize-y ${
                hasError
                  ? 'border-red-300 focus:ring-red-500 focus:border-red-500 bg-red-50'
                  : hasWarning
                  ? 'border-yellow-300 focus:ring-yellow-500 focus:border-yellow-500'
                  : 'border-gray-300 focus:ring-lucid-500 focus:border-lucid-500'
              }`}
            />
            {hasError && (
              <p className="text-xs text-red-600">
                {validationErrors[prompt.key]}
              </p>
            )}
            {!hasError && hasWarning && (
              <p className="text-xs text-yellow-600">
                {validationWarnings[prompt.key]}
              </p>
            )}

            {/* Variables Documentation */}
            <details className="mt-2">
              <summary className="text-xs text-gray-600 cursor-pointer hover:text-gray-800 select-none">
                📋 Required variables ({prompt.variables?.length || 0})
              </summary>
              <div className="mt-2 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <ul className="space-y-1 text-xs text-gray-700 font-mono">
                  {prompt.variables?.map((variable, idx) => (
                    <li key={idx} className="leading-relaxed">
                      {variable}
                    </li>
                  ))}
                </ul>
              </div>
            </details>
          </div>
        );
      })}
    </div>
  );
}

// Instructions Tab Component
function InstructionsTab({ config, onChange }: {
  config: AppConfig;
  onChange: (updates: Partial<StageInstructionsConfig>) => void;
}) {
  const stages = [
    { key: 'stage1' as keyof StageInstructionsConfig, label: 'Stage 1 (Draft)', description: 'Default instructions for generating slide texts' },
    { key: 'stage_style' as keyof StageInstructionsConfig, label: 'Stage Style', description: 'Default instructions for style proposals' },
    { key: 'stage2' as keyof StageInstructionsConfig, label: 'Stage 2 (Prompts)', description: 'Default instructions for image prompts' },
    { key: 'stage3' as keyof StageInstructionsConfig, label: 'Stage 3 (Images)', description: 'Instructions for image generation (if needed)' },
  ];

  return (
    <div className="space-y-6">
      <p className="text-sm text-gray-600">
        Set default additional instructions for each stage. These will be used when no explicit instructions are provided.
        Leave empty to use no default instructions.
      </p>

      {stages.map((stage) => (
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

// Global Tab Component
function GlobalTab({ config, onChange }: {
  config: AppConfig;
  onChange: (updates: Partial<GlobalDefaultsConfig>) => void;
}) {
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

// Image Tab Component
function ImageTab({ config, onChange }: {
  config: AppConfig;
  onChange: (updates: Partial<ImageConfig>) => void;
}) {
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

// Style Tab Component
function StyleTab({ config, onChange }: {
  config: AppConfig;
  onChange: (updates: Partial<StyleConfig>) => void;
}) {
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
