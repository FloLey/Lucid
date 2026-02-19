"""API routes for editing prompt files directly."""

from typing import Dict
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.dependencies import container
from app.services.prompt_validator import validate_prompt, validate_all_prompts

router = APIRouter()

prompt_loader = container.prompt_loader


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
    """Load all prompts from .prompt files."""
    try:
        prompts = prompt_loader.load_all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read prompts: {e}")
    return GetPromptsResponse(prompts=prompts)


@router.put("/{prompt_name}")
async def update_prompt(prompt_name: str, request: UpdatePromptRequest):
    """Update a single prompt file."""
    if not prompt_loader.is_known(prompt_name):
        raise HTTPException(status_code=404, detail=f"Unknown prompt: {prompt_name}")

    is_valid, error_msg = validate_prompt(prompt_name, request.content)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Validation failed: {error_msg}")

    try:
        prompt_loader.save(prompt_name, request.content)
        return {"message": f"Updated {prompt_name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write {prompt_name}: {e}")


@router.patch("")
async def update_prompts(request: UpdatePromptsRequest):
    """Update multiple prompt files at once."""
    updated_count = 0
    errors = []

    for name, content in request.prompts.items():
        if not prompt_loader.is_known(name):
            errors.append(f"Unknown prompt: {name}")
            continue

        is_valid, error_msg = validate_prompt(name, content)
        if not is_valid:
            errors.append(f"{name}: {error_msg}")
            continue

        try:
            prompt_loader.save(name, content)
            updated_count += 1
        except Exception as e:
            errors.append(f"{name}: Failed to write - {e}")

    if errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))

    return {"message": f"Updated {updated_count} prompt files"}


@router.post("/validate", response_model=ValidatePromptsResponse)
async def validate_prompts_endpoint(request: UpdatePromptsRequest):
    """Validate prompts without saving them."""
    try:
        validation_results = validate_all_prompts(request.prompts)

        errors = {}
        warnings = {}

        for name, message in validation_results.items():
            if "Missing required variables" in message:
                errors[name] = message
            else:
                warnings[name] = message

        return ValidatePromptsResponse(
            valid=len(errors) == 0, errors=errors, warnings=warnings
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
        detail="Reset not implemented. Use git to restore original prompts.",
    )
