"""Chat service for natural language command routing."""

import json
import logging
import re
from typing import Optional, Dict, Any, Tuple

from app.services.gemini_service import gemini_service
from app.services.session_manager import session_manager
from app.services.stage1_service import stage1_service
from app.services.stage2_service import stage2_service
from app.services.stage3_service import stage3_service
from app.services.stage4_service import stage4_service

logger = logging.getLogger(__name__)


TOOL_ROUTING_PROMPT = """You are an AI assistant for Lucid, a carousel creation tool.
Your job is to interpret user commands and route them to the appropriate tool.

Available tools:
1. next_stage - Advance to the next stage
2. go_to_stage - Go to a specific stage (1-4)
3. generate_slides - Generate slide texts from draft (Stage 1)
4. regenerate_slide - Regenerate a single slide's text
5. update_slide - Update a slide's text manually
6. generate_prompts - Generate image prompts from slide texts (Stage 2)
7. regenerate_prompt - Regenerate a single slide's image prompt
8. update_prompt - Update a slide's image prompt manually
9. generate_images - Generate background images (Stage 3)
10. regenerate_image - Regenerate a single slide's background image
11. apply_styles - Apply text styling to images (Stage 4)
12. update_style - Update styling for a slide
13. apply_preset - Apply a style preset to slides

User message: {message}

Analyze the user's intent and respond with a JSON object:
{{
    "tool": "tool_name",
    "params": {{}},
    "response": "A brief response to the user"
}}

For tool params:
- slide_index: 0-based index (when user says "slide 3", use index 2)
- text/body/title: string content
- style: object with style properties
- preset: one of "modern", "bold", "elegant", "minimal", "impact"

If the message is just a greeting or general question, respond with:
{{
    "tool": null,
    "response": "Your helpful response"
}}

Respond with valid JSON only.
"""


class ChatService:
    """Service for chat-based command interface."""

    # Regex patterns for explicit commands
    COMMAND_PATTERNS = {
        r"^/next$": ("next_stage", {}),
        r"^/stage\s+(\d)$": ("go_to_stage", lambda m: {"stage": int(m.group(1))}),
        r"^/regen\s+slide\s+(\d+)$": ("regenerate_slide", lambda m: {"slide_index": int(m.group(1)) - 1}),
        r"^/regen\s+prompt\s+(\d+)$": ("regenerate_prompt", lambda m: {"slide_index": int(m.group(1)) - 1}),
        r"^/regen\s+image\s+(\d+)$": ("regenerate_image", lambda m: {"slide_index": int(m.group(1)) - 1}),
        r"^/apply\s+preset\s+(\w+)$": ("apply_preset", lambda m: {"preset": m.group(1)}),
    }

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

        # Check for explicit commands first
        tool, params = self._parse_explicit_command(message)

        if not tool:
            # Use LLM for natural language routing
            tool, params, response = await self._route_with_llm(message)

            if not tool:
                return {
                    "success": True,
                    "response": response,
                    "tool_called": None,
                    "session": session.model_dump(),
                }
        else:
            response = None

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
    ) -> Tuple[Optional[str], Dict[str, Any], str]:
        """Use LLM to route natural language commands."""
        prompt = TOOL_ROUTING_PROMPT.format(message=message)
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

            elif tool == "go_to_stage":
                stage = params.get("stage", 1)
                session = session_manager.go_to_stage(session_id, stage)
                response = f"Now at Stage {stage}" if session else "Failed"

            elif tool == "regenerate_slide":
                slide_index = params.get("slide_index", 0)
                session = await stage1_service.regenerate_slide_text(session_id, slide_index)
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

            elif tool == "apply_preset":
                preset = params.get("preset", "modern")
                presets = {
                    "modern": {"font_family": "Inter", "font_weight": 700, "stroke": {"enabled": True, "width_px": 2}},
                    "bold": {"font_family": "Oswald", "font_weight": 700, "font_size_px": 80},
                    "elegant": {"font_family": "Playfair Display", "shadow": {"enabled": True}},
                    "minimal": {"font_family": "Roboto", "font_weight": 400, "alignment": "left"},
                    "impact": {"font_family": "Montserrat", "font_weight": 700, "text_color": "#FFFF00"},
                }
                style = presets.get(preset, presets["modern"])
                session = stage4_service.apply_style_to_all(session_id, style)
                response = f"Applied '{preset}' preset to all slides"

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
