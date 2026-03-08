"""Unit tests for app/services/prompt_validator.py."""

import pytest

from app.services.prompt_validator import (
    PromptValidator,
    extract_variables,
    validate_all_prompts,
    validate_prompt,
)


# ── extract_variables ──────────────────────────────────────────────────────


class TestExtractVariables:
    def test_extracts_single_variable(self):
        assert extract_variables("Hello {name}") == {"name"}

    def test_extracts_multiple_variables(self):
        result = extract_variables("{foo} and {bar} and {baz}")
        assert result == {"foo", "bar", "baz"}

    def test_ignores_escaped_braces(self):
        # {{escaped}} should not be treated as a variable
        result = extract_variables("{{not_a_var}} but {real_var}")
        assert result == {"real_var"}

    def test_empty_prompt_returns_empty_set(self):
        assert extract_variables("no placeholders here") == set()

    def test_deduplicates_repeated_variable(self):
        assert extract_variables("{x} and {x} again") == {"x"}

    def test_variable_with_underscores_and_digits(self):
        assert extract_variables("{var_1} {var_2}") == {"var_1", "var_2"}


# ── validate_prompt ────────────────────────────────────────────────────────


class TestValidatePrompt:
    def test_valid_prompt_all_required_vars_present(self):
        content = (
            "{num_proposals} {slides_text} {additional_instructions} {response_format}"
        )
        ok, msg = validate_prompt("style_proposal", content)
        assert ok is True
        assert msg == ""

    def test_missing_required_variable_returns_false(self):
        # Omit response_format intentionally
        content = "{num_proposals} {slides_text} {additional_instructions}"
        ok, msg = validate_prompt("style_proposal", content)
        assert ok is False
        assert "Missing required variables" in msg
        assert "response_format" in msg

    def test_extra_variables_returns_true_with_note(self):
        # Include all required vars plus an extra one
        content = (
            "{num_proposals} {slides_text} {additional_instructions} "
            "{response_format} {extra_var}"
        )
        ok, msg = validate_prompt("style_proposal", content)
        assert ok is True
        assert "extra_var" in msg  # note about unexpected variable

    def test_unknown_prompt_name_returns_false(self):
        ok, msg = validate_prompt("nonexistent_prompt_type", "some content")
        assert ok is False
        assert "Unknown prompt type" in msg

    def test_missing_multiple_vars_lists_all(self):
        ok, msg = validate_prompt("style_proposal", "no variables here")
        assert ok is False
        # All four required vars should be flagged
        for var in ("num_proposals", "slides_text", "additional_instructions", "response_format"):
            assert var in msg

    def test_slide_generation_prompt_valid(self):
        content = (
            "{num_slides_instruction} {language_instruction} {title_instruction} "
            "{additional_instructions} {draft} {slide_format} {response_format}"
        )
        ok, msg = validate_prompt("slide_generation", content)
        assert ok is True
        assert msg == ""


# ── validate_all_prompts ───────────────────────────────────────────────────


class TestValidateAllPrompts:
    def test_all_valid_returns_empty_dict(self):
        prompts = {
            "style_proposal": (
                "{num_proposals} {slides_text} {additional_instructions} {response_format}"
            ),
        }
        result = validate_all_prompts(prompts)
        assert result == {}

    def test_invalid_prompt_appears_in_result(self):
        prompts = {"style_proposal": "missing all vars"}
        result = validate_all_prompts(prompts)
        assert "style_proposal" in result
        assert "Missing required variables" in result["style_proposal"]

    def test_unknown_prompt_name_appears_in_result(self):
        prompts = {"unknown_xyz": "content"}
        result = validate_all_prompts(prompts)
        assert "unknown_xyz" in result

    def test_mix_of_valid_and_invalid(self):
        prompts = {
            "style_proposal": (
                "{num_proposals} {slides_text} {additional_instructions} {response_format}"
            ),
            "slide_generation": "incomplete prompt",
        }
        result = validate_all_prompts(prompts)
        assert "style_proposal" not in result
        assert "slide_generation" in result

    def test_empty_dict_returns_empty_dict(self):
        assert validate_all_prompts({}) == {}


# ── PromptValidator class ──────────────────────────────────────────────────


class TestPromptValidatorClass:
    def setup_method(self):
        self.validator = PromptValidator()

    def test_validate_prompt_delegates_correctly(self):
        content = (
            "{num_proposals} {slides_text} {additional_instructions} {response_format}"
        )
        ok, msg = self.validator.validate_prompt("style_proposal", content)
        assert ok is True

    def test_validate_prompt_missing_var(self):
        ok, msg = self.validator.validate_prompt("style_proposal", "no vars")
        assert ok is False

    def test_validate_all_prompts_delegates_correctly(self):
        prompts = {"style_proposal": "missing vars"}
        result = self.validator.validate_all_prompts(prompts)
        assert "style_proposal" in result
