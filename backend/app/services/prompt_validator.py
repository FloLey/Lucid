"""Prompt validation service to ensure required variables are present."""

import re
from typing import Dict, List, Set


# Required variables for each prompt type
REQUIRED_VARIABLES: Dict[str, Set[str]] = {
    "slide_generation": {
        "num_slides_instruction",
        "language_instruction",
        "title_instruction",
        "additional_instructions",
        "draft",
        "slide_format",
        "response_format",
    },
    "style_proposal": {
        "num_proposals",
        "slides_text",
        "additional_instructions",
        "response_format",
    },
    "generate_single_image_prompt": {
        "slide_text",
        "shared_theme",
        "style_instructions_text",
        "context",
        "instruction_text",
        "response_format",
    },
    "regenerate_single_slide": {
        "draft_text",
        "language_instruction",
        "all_slides_context",
        "current_text",
        "instruction_text",
        "title_instruction",
        "response_format",
    },
    "chat_routing": {
        "current_stage",
        "tool_descriptions",
        "message",
        "response_format",
    },
}


def extract_variables(prompt: str) -> Set[str]:
    """Extract all {variable} placeholders from a prompt string."""
    # Match {variable_name} but not {{escaped}}
    pattern = r"(?<!\{)\{([a-zA-Z_][a-zA-Z0-9_]*)\}(?!\})"
    return set(re.findall(pattern, prompt))


def validate_prompt(prompt_name: str, prompt_text: str) -> tuple[bool, str]:
    """
    Validate that a prompt contains all required variables.

    Args:
        prompt_name: Name of the prompt (e.g., "slide_generation")
        prompt_text: The prompt text to validate

    Returns:
        Tuple of (is_valid, error_message)
        If valid, error_message is empty string
    """
    if prompt_name not in REQUIRED_VARIABLES:
        return False, f"Unknown prompt type: {prompt_name}"

    required = REQUIRED_VARIABLES[prompt_name]
    found = extract_variables(prompt_text)

    missing = required - found
    extra = found - required

    errors = []

    if missing:
        errors.append(f"Missing required variables: {', '.join(sorted(missing))}")

    # Extra variables are a warning, not an error (might be intentional)
    # But we'll include them in the message for awareness
    if extra:
        errors.append(f"Note: Found unexpected variables: {', '.join(sorted(extra))}")

    if missing:
        return False, " | ".join(errors)

    # Valid, but include warning about extra variables
    if extra:
        return True, errors[0]  # Return the note about extra variables

    return True, ""


def validate_all_prompts(prompts: Dict[str, str]) -> Dict[str, str]:
    """
    Validate all prompts in a PromptsConfig dict.

    Args:
        prompts: Dictionary mapping prompt names to prompt text

    Returns:
        Dictionary mapping prompt names to error messages (empty if valid)
    """
    results = {}

    for prompt_name, prompt_text in prompts.items():
        is_valid, message = validate_prompt(prompt_name, prompt_text)
        if not is_valid or message:  # Include warnings too
            results[prompt_name] = message

    return results
