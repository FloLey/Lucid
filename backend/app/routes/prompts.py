"""API routes for editing prompt files directly."""

from pathlib import Path
from typing import Dict
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.prompt_validator import validate_prompt

router = APIRouter()

PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"

# Map of prompt names to their filenames
PROMPT_FILES = {
    "slide_generation": "slide_generation.prompt",
    "style_proposal": "style_proposal.prompt",
    "generate_single_image_prompt": "generate_single_image_prompt.prompt",
    "regenerate_single_slide": "regenerate_single_slide.prompt",
    "chat_routing": "chat_routing.prompt",
}


class GetPromptsResponse(BaseModel):
    """Response containing all prompts loaded from files."""
    prompts: Dict[str, str]


class UpdatePromptRequest(BaseModel):
    """Request to update a single prompt file."""
    prompt_name: str
    content: str


class UpdatePromptsRequest(BaseModel):
    """Request to update multiple prompt files."""
    prompts: Dict[str, str]


class ValidatePromptsResponse(BaseModel):
    """Response from prompt validation."""
    valid: bool
    errors: Dict[str, str]
    warnings: Dict[str, str]


@router.get("", response_model=GetPromptsResponse)
async def get_prompts():
    """Load all prompts from .prompt files.

    Returns:
        GetPromptsResponse: All prompt contents
    """
    prompts = {}
    for name, filename in PROMPT_FILES.items():
        filepath = PROMPTS_DIR / filename
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                prompts[name] = f.read()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to read {filename}: {e}")

    return GetPromptsResponse(prompts=prompts)


@router.put("/{prompt_name}")
async def update_prompt(prompt_name: str, request: UpdatePromptRequest):
    """Update a single prompt file.

    Args:
        prompt_name: Name of the prompt to update
        request: New content

    Returns:
        Success message
    """
    if prompt_name not in PROMPT_FILES:
        raise HTTPException(status_code=404, detail=f"Unknown prompt: {prompt_name}")

    # Validate the prompt
    is_valid, error_msg = validate_prompt(prompt_name, request.content)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Validation failed: {error_msg}")

    # Write to file
    filename = PROMPT_FILES[prompt_name]
    filepath = PROMPTS_DIR / filename
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(request.content)
        return {"message": f"Updated {filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write {filename}: {e}")


@router.patch("")
async def update_prompts(request: UpdatePromptsRequest):
    """Update multiple prompt files at once.

    Args:
        request: Dictionary of prompt names to new content

    Returns:
        Success message with count of updated files
    """
    updated_count = 0
    errors = []

    for name, content in request.prompts.items():
        if name not in PROMPT_FILES:
            errors.append(f"Unknown prompt: {name}")
            continue

        # Validate
        is_valid, error_msg = validate_prompt(name, content)
        if not is_valid:
            errors.append(f"{name}: {error_msg}")
            continue

        # Write to file
        filename = PROMPT_FILES[name]
        filepath = PROMPTS_DIR / filename
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            updated_count += 1
        except Exception as e:
            errors.append(f"{name}: Failed to write - {e}")

    if errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))

    return {"message": f"Updated {updated_count} prompt files"}


@router.post("/validate", response_model=ValidatePromptsResponse)
async def validate_prompts_endpoint(request: UpdatePromptsRequest):
    """Validate prompts without saving them.

    Args:
        request: Prompts to validate

    Returns:
        ValidatePromptsResponse: Validation results
    """
    from app.services.prompt_validator import validate_all_prompts

    try:
        validation_results = validate_all_prompts(request.prompts)

        # Separate errors from warnings
        errors = {}
        warnings = {}

        for name, message in validation_results.items():
            if "Missing required variables" in message:
                errors[name] = message
            else:
                warnings[name] = message

        is_valid = len(errors) == 0

        return ValidatePromptsResponse(
            valid=is_valid,
            errors=errors,
            warnings=warnings
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reset")
async def reset_prompts():
    """Reset is not applicable - prompts are in files.

    Users should restore from git or manually revert changes.
    """
    raise HTTPException(
        status_code=501,
        detail="Reset not implemented. Use git to restore original prompts."
    )
