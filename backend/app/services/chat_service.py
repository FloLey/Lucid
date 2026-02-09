"""Chat service for natural language command routing."""

import json
import logging
import re
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

from app.services.gemini_service import gemini_service
from app.services.session_manager import session_manager
from app.services.stage1_service import stage1_service
from app.services.stage_style_service import stage_style_service
from app.services.stage2_service import stage2_service
from app.services.stage3_service import stage3_service
from app.services.stage4_service import stage4_service
from app.services.export_service import export_service

logger = logging.getLogger(__name__)


def _load_prompt_file(filename: str) -> str:
    """Load a prompt from the prompts directory."""
    prompt_path = Path(__file__).parent.parent.parent / "prompts" / filename
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Failed to load prompt file {filename}: {e}")
        return ""


def _get_chat_routing_prompt() -> str:
    """Get chat routing prompt from file."""
    return _load_prompt_file("chat_routing.prompt")


# Tools allowed per stage - prevents hallucinations and logic errors
STAGE_ALLOWED_TOOLS = {
    1: {"generate_slides", "regenerate_slide", "update_slide", "next_stage", "go_to_stage", "back_stage"},
    2: {"generate_style_proposals", "select_style_proposal", "next_stage", "go_to_stage", "back_stage"},
    3: {"generate_prompts", "regenerate_prompt", "update_prompt", "next_stage", "go_to_stage", "back_stage"},
    4: {"generate_images", "regenerate_image", "next_stage", "go_to_stage", "back_stage"},
    5: {"apply_styles", "update_style", "export", "go_to_stage", "back_stage"},
}

# Human-friendly tool descriptions per stage
STAGE_TOOL_DESCRIPTIONS = {
    1: """
1. generate_slides - Generate slide texts from draft
2. regenerate_slide - Regenerate a single slide's text
3. update_slide - Update a slide's text manually
4. next_stage - Advance to Stage 2
5. back_stage - Go to previous stage""",
    2: """
1. generate_style_proposals - Generate visual style proposals with previews
2. select_style_proposal - Select a style proposal by index
3. next_stage - Advance to Stage 3
4. back_stage - Go back to Stage 1""",
    3: """
1. generate_prompts - Generate image prompts from slide texts
2. regenerate_prompt - Regenerate a single slide's image prompt
3. update_prompt - Update a slide's image prompt manually
4. next_stage - Advance to Stage 4
5. back_stage - Go back to Stage 2""",
    4: """
1. generate_images - Generate background images
2. regenerate_image - Regenerate a single slide's background image
3. next_stage - Advance to Stage 5
4. back_stage - Go back to Stage 3""",
    5: """
1. apply_styles - Apply text styling to images
2. update_style - Update styling for a slide
3. export - Export carousel as ZIP
4. back_stage - Go back to Stage 4""",
}

# Error messages for tools used in wrong stage
STAGE_ERROR_MESSAGES = {
    "generate_style_proposals": "Please advance to Stage 2 to generate style proposals. Use /next to proceed.",
    "generate_prompts": "Please advance to Stage 3 to generate image prompts. Use /next to proceed.",
    "generate_images": "Please advance to Stage 4 to generate images. Use /next to proceed.",
    "apply_styles": "Please advance to Stage 5 to apply styles. Use /next to proceed.",
    "export": "Please advance to Stage 5 to export your carousel. Use /next to proceed.",
}


def get_routing_prompt(current_stage: int) -> str:
    """Generate stage-scoped routing prompt with only allowed tools."""
    tool_descriptions = STAGE_TOOL_DESCRIPTIONS.get(current_stage, "")

    # Get prompt template from config
    prompt_template = _get_chat_routing_prompt()

    response_format = '''{{
    "tool": "tool_name",
    "params": {{}},
    "response": "A brief response to the user"
}}

Or if just a greeting/question:
{{
    "tool": null,
    "response": "Your helpful response"
}}'''

    return prompt_template.format(
        current_stage=current_stage,
        tool_descriptions=tool_descriptions,
        message="{message}",  # Keep as template variable for later
        response_format=response_format,
    )


class ChatService:
    """Service for chat-based command interface with stage-scoped tool validation."""

    # Regex patterns for explicit commands
    COMMAND_PATTERNS = {
        r"^/next$": ("next_stage", {}),
        r"^/back$": ("back_stage", {}),
        r"^/stage\s+(\d)$": ("go_to_stage", lambda m: {"stage": int(m.group(1))}),
        r"^/regen\s+slide\s+(\d+)$": ("regenerate_slide", lambda m: {"slide_index": int(m.group(1)) - 1}),
        r"^/regen\s+prompt\s+(\d+)$": ("regenerate_prompt", lambda m: {"slide_index": int(m.group(1)) - 1}),
        r"^/regen\s+image\s+(\d+)$": ("regenerate_image", lambda m: {"slide_index": int(m.group(1)) - 1}),
        r"^/generate$": ("auto_generate", {}),
        r"^/export$": ("export", {}),
    }

    def _validate_tool_for_stage(self, tool: str, current_stage: int) -> Optional[str]:
        """
        Validate if a tool can be used in the current stage.

        Returns error message if invalid, None if valid.
        """
        allowed_tools = STAGE_ALLOWED_TOOLS.get(current_stage, set())

        # Navigation tools are always allowed
        if tool in {"next_stage", "go_to_stage", "back_stage"}:
            return None

        # Auto-generate maps to the appropriate tool for the current stage
        if tool == "auto_generate":
            return None

        if tool not in allowed_tools:
            # Get a friendly error message
            error = STAGE_ERROR_MESSAGES.get(
                tool,
                f"The '{tool}' command is not available in Stage {current_stage}. "
                f"Available commands: {', '.join(sorted(allowed_tools))}"
            )
            return error

        return None

    async def process_message(
        self,
        session_id: str,
        message: str,
    ) -> Dict[str, Any]:
        """Process a chat message and execute appropriate action."""
        session = session_manager.get_session(session_id)
        if not session:
            return {
                "success": False,
                "response": "No active session. Please start a new session first.",
                "tool_called": None,
            }

        current_stage = session.current_stage

        # Check for explicit commands first
        tool, params = self._parse_explicit_command(message)

        if not tool:
            # Use LLM for natural language routing with stage-scoped prompt
            tool, params, response = await self._route_with_llm(message, current_stage)

            if not tool:
                return {
                    "success": True,
                    "response": response,
                    "tool_called": None,
                    "session": session.model_dump(),
                }
        else:
            response = None

        # Validate tool is allowed in current stage
        validation_error = self._validate_tool_for_stage(tool, current_stage)
        if validation_error:
            return {
                "success": False,
                "response": validation_error,
                "tool_called": tool,
                "session": session.model_dump(),
            }

        # Handle auto_generate - map to appropriate tool for current stage
        if tool == "auto_generate":
            stage_tools = {
                1: "generate_slides",
                2: "generate_style_proposals",
                3: "generate_prompts",
                4: "generate_images",
                5: "apply_styles",
            }
            tool = stage_tools.get(current_stage, tool)

        # Execute the tool
        result = await self._execute_tool(session_id, tool, params)

        return {
            "success": result["success"],
            "response": result.get("response") or response or f"Executed {tool}",
            "tool_called": tool,
            "session": result.get("session"),
        }

    def _parse_explicit_command(self, message: str) -> Tuple[Optional[str], Dict[str, Any]]:
        """Parse explicit slash commands."""
        message = message.strip()

        for pattern, (tool, params_fn) in self.COMMAND_PATTERNS.items():
            match = re.match(pattern, message, re.IGNORECASE)
            if match:
                if callable(params_fn):
                    params = params_fn(match)
                else:
                    params = params_fn
                return tool, params

        return None, {}

    async def _route_with_llm(
        self,
        message: str,
        current_stage: int = 1,
    ) -> Tuple[Optional[str], Dict[str, Any], str]:
        """Use LLM to route natural language commands with stage-scoped tools."""
        # Generate stage-specific routing prompt
        routing_prompt = get_routing_prompt(current_stage)
        prompt = routing_prompt.format(message=message)

        result = await gemini_service.generate_json(prompt)

        tool = result.get("tool")
        params = result.get("params", {})
        response = result.get("response", "I'll help you with that.")

        return tool, params, response

    async def _execute_tool(
        self,
        session_id: str,
        tool: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a tool action."""
        try:
            session = None

            if tool == "next_stage":
                session = session_manager.advance_stage(session_id)
                response = f"Advanced to Stage {session.current_stage}" if session else "Failed"

            elif tool == "back_stage":
                session = session_manager.previous_stage(session_id)
                response = f"Returned to Stage {session.current_stage}" if session else "Failed"

            elif tool == "go_to_stage":
                stage = params.get("stage", 1)
                session = session_manager.go_to_stage(session_id, stage)
                response = f"Now at Stage {stage}" if session else "Failed"

            elif tool == "regenerate_slide":
                slide_index = params.get("slide_index", 0)
                instruction = params.get("instruction")
                session = await stage1_service.regenerate_slide_text(session_id, slide_index, instruction=instruction)
                response = f"Regenerated slide {slide_index + 1}"

            elif tool == "update_slide":
                slide_index = params.get("slide_index", 0)
                session = stage1_service.update_slide_text(
                    session_id,
                    slide_index,
                    title=params.get("title"),
                    body=params.get("body"),
                )
                response = f"Updated slide {slide_index + 1}"

            elif tool == "generate_style_proposals":
                num = params.get("num_proposals", 3)
                instructions = params.get("additional_instructions")
                session = await stage_style_service.generate_proposals(
                    session_id, num_proposals=num, additional_instructions=instructions,
                )
                response = f"Generated {num} style proposals"

            elif tool == "select_style_proposal":
                proposal_index = params.get("proposal_index", 0)
                session = stage_style_service.select_proposal(session_id, proposal_index)
                response = f"Selected style proposal {proposal_index + 1}"

            elif tool == "generate_prompts":
                session = await stage2_service.generate_all_prompts(
                    session_id,
                    image_style_instructions=params.get("style_instructions"),
                )
                response = "Generated image prompts for all slides"

            elif tool == "regenerate_prompt":
                slide_index = params.get("slide_index", 0)
                session = await stage2_service.regenerate_prompt(session_id, slide_index)
                response = f"Regenerated prompt for slide {slide_index + 1}"

            elif tool == "update_prompt":
                slide_index = params.get("slide_index", 0)
                session = stage2_service.update_prompt(
                    session_id,
                    slide_index,
                    params.get("prompt", ""),
                )
                response = f"Updated prompt for slide {slide_index + 1}"

            elif tool == "generate_images":
                session = await stage3_service.generate_all_images(session_id)
                response = "Generated background images for all slides"

            elif tool == "regenerate_image":
                slide_index = params.get("slide_index", 0)
                session = await stage3_service.regenerate_image(session_id, slide_index)
                response = f"Regenerated image for slide {slide_index + 1}"

            elif tool == "apply_styles":
                session = await stage4_service.apply_text_to_all_images(session_id)
                response = "Applied text styling to all slides"

            elif tool == "update_style":
                slide_index = params.get("slide_index", 0)
                style = params.get("style", {})
                session = stage4_service.update_style(session_id, slide_index, style)
                response = f"Updated style for slide {slide_index + 1}"

            elif tool == "export":
                session = session_manager.get_session(session_id)
                if session:
                    # Generate the ZIP but respond with download instructions
                    response = "Your carousel is ready! Click the Export button to download your ZIP file."
                else:
                    response = "No session found for export."

            else:
                return {
                    "success": False,
                    "response": f"Unknown tool: {tool}",
                }

            return {
                "success": session is not None,
                "response": response,
                "session": session.model_dump() if session else None,
            }

        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return {
                "success": False,
                "response": f"Error executing {tool}: {str(e)}",
            }


# Global chat service instance
chat_service = ChatService()
