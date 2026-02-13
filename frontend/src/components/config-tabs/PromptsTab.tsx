import { useState, useEffect } from 'react';
import * as api from '../../services/api';

const PROMPT_LIST = [
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

interface PromptsTabProps {
  prompts: Record<string, string>;
  onChange: (updates: Record<string, string>) => void;
  onValidationChange: (hasErrors: boolean) => void;
}

export default function PromptsTab({ prompts, onChange, onValidationChange }: PromptsTabProps) {
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});
  const [validationWarnings, setValidationWarnings] = useState<Record<string, string>>({});
  const [validating, setValidating] = useState(false);

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
            Tip: These files are version-controlled. Use git to restore originals if needed.
          </p>
        </div>
      </div>

      {PROMPT_LIST.map((prompt) => {
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
                  <span className="text-xs text-red-600 font-medium">Invalid</span>
                )}
                {!hasError && hasWarning && (
                  <span className="text-xs text-yellow-600 font-medium">Warning</span>
                )}
                {!hasError && !hasWarning && !validating && (
                  <span className="text-xs text-green-600 font-medium">Valid</span>
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
                Required variables ({prompt.variables?.length || 0})
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
