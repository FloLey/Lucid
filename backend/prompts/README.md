# Lucid Prompts

This directory contains the AI prompts used throughout Lucid. These `.prompt` files are:

1. **Version controlled** - Committed to Git (track changes over time)
2. **User-editable** - Edit via Settings UI or directly in your editor
3. **Single source of truth** - NOT stored in config.json

## Prompt Files

- `generate_draft_from_research.prompt` - Synthesise a research chat conversation into a structured draft (Stage Research)
- `slide_generation.prompt` - Generate all slide texts from a draft (Stage Draft)
- `style_proposal.prompt` - Generate visual style proposals (Stage Style)
- `generate_single_image_prompt.prompt` - Generate per-slide image prompts in parallel (Stage Prompts, also used for regeneration)
- `regenerate_single_slide.prompt` - Regenerate a single slide's text with full carousel context
- `generate_project_title.prompt` - Generate a short title for a project

## How It Works

Services load prompts **directly from these files**:
1. Service calls `_get_*_prompt()` function
2. Function reads from `config_manager` (which loads from `.prompt` files)
3. If that fails, fallback to reading `.prompt` file directly
4. Prompts are NOT stored in `config.json`

## Editing Prompts

**Via Settings UI:**
1. Click Settings button in header
2. Go to Prompts tab
3. Edit any prompt
4. Click Save → **writes directly to `.prompt` files**

**Via File Editor:**
1. Open any `.prompt` file in your editor
2. Make changes
3. Save → backend auto-reloads on next use (Docker volume mounted)

**Restoring Defaults:**
- Use `git checkout backend/prompts/` to restore original prompts
- Or `git diff backend/prompts/` to see your changes

## Required Variables

Each prompt **must** include specific template variables (validated before save):

**generate_draft_from_research.prompt:**
- `{transcript}`, `{instructions}`
- Receives a formatted transcript of the research conversation and optional user instructions

**slide_generation.prompt:**
- `{num_slides_instruction}`, `{language_instruction}`, `{title_instruction}`, `{additional_instructions}`, `{draft}`, `{slide_format}`, `{response_format}`

**style_proposal.prompt:**
- `{num_proposals}`, `{slides_text}`, `{additional_instructions}`, `{response_format}`
- Returns `description` = single image prompt (used for preview + prepended to all slides)

**generate_single_image_prompt.prompt:**
- `{slide_text}`, `{shared_theme}`, `{style_instructions_text}`, `{context}`, `{instruction_text}`, `{response_format}`
- Generates one prompt per slide in parallel (shared theme prepended in Stage Prompts)
- Reused for regeneration with optional instruction parameter

**regenerate_single_slide.prompt:**
- `{draft_text}`, `{language_instruction}`, `{all_slides_context}`, `{current_text}`, `{instruction_text}`, `{title_instruction}`, `{response_format}`

## Validation

The Settings UI validates prompts in real-time:
- ✅ **Valid** - All required variables present
- ⚠️ **Warning** - Extra variables found (allowed)
- ❌ **Error** - Missing required variables (blocks save)

Validation also runs on the backend before writing files.

## Best Practices

- Use git to track your prompt changes over time
- Test prompts with real data after editing
- Keep prompts focused and specific
- Include all required `{variables}` for your prompt to work
- Use clear, direct language (the AI reads these as instructions)
