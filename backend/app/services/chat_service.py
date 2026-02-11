"""Chat service with agentic tool loop and SSE streaming."""

import json
import logging
import re
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, AsyncGenerator

from app.services.gemini_service import gemini_service, GeminiError
from app.services.session_manager import session_manager
from app.services.stage1_service import stage1_service
from app.services.stage_style_service import stage_style_service
from app.services.stage2_service import stage2_service
from app.services.stage3_service import stage3_service
from app.services.stage4_service import stage4_service

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


# In-memory cancellation flags (one per session)
_cancel_flags: Dict[str, bool] = {}

# Read tools are never stage-gated
READ_TOOLS = {"get_slide", "get_all_slides", "get_draft", "get_session_info", "get_style_proposals"}

# Navigation tools are always available
NAV_TOOLS = {"next_stage", "back_stage", "go_to_stage"}

# Write tools allowed per stage
STAGE_WRITE_TOOLS: Dict[int, set] = {
    1: {"generate_slides", "regenerate_slide", "update_slide"},
    2: {"generate_style_proposals", "select_style_proposal"},
    3: {"generate_prompts", "regenerate_prompt", "update_prompt"},
    4: {"generate_images", "regenerate_image"},
    5: {"apply_styles", "update_style", "export"},
}

# Combined for backward compat: all tools per stage (read + write + nav)
STAGE_ALLOWED_TOOLS = {
    stage: tools | NAV_TOOLS
    for stage, tools in STAGE_WRITE_TOOLS.items()
}

# Regex patterns for explicit slash commands (fast path, bypasses LLM)
COMMAND_PATTERNS = {
    r"^/next$": ("next_stage", {}),
    r"^/back$": ("back_stage", {}),
    r"^/stage\s+(\d)$": ("go_to_stage", lambda m: {"stage": int(m.group(1))}),
    r"^/regen\s+slide\s+(\d+)$": ("regenerate_slide", lambda m: {"slide_index": int(m.group(1))}),
    r"^/regen\s+prompt\s+(\d+)$": ("regenerate_prompt", lambda m: {"slide_index": int(m.group(1))}),
    r"^/regen\s+image\s+(\d+)$": ("regenerate_image", lambda m: {"slide_index": int(m.group(1))}),
    r"^/generate$": ("auto_generate", {}),
    r"^/export$": ("export", {}),
}

MAX_AGENT_ITERATIONS = 5


def _sse_event(event: str, data: Any) -> str:
    """Format a Server-Sent Event line."""
    return f"data: {json.dumps({'event': event, **data})}\n\n"


def _get_tool_declarations(current_stage: int) -> list:
    """Build function declarations for read + stage-gated write + navigation tools."""
    declarations = [
        # Read tools (always available)
        {
            "name": "get_slide",
            "description": "Get the full content of a specific slide (title, body, image prompt, style summary).",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "slide_index": {
                        "type": "INTEGER",
                        "description": "1-based slide number (e.g., 1 for slide 1)",
                    }
                },
                "required": ["slide_index"],
            },
        },
        {
            "name": "get_all_slides",
            "description": "Get a summary of all slides (index, title, body snippet).",
            "parameters": {"type": "OBJECT", "properties": {}},
        },
        {
            "name": "get_draft",
            "description": "Get the original draft text the user provided.",
            "parameters": {"type": "OBJECT", "properties": {}},
        },
        {
            "name": "get_session_info",
            "description": "Get session metadata: current stage, number of slides, language, selected style.",
            "parameters": {"type": "OBJECT", "properties": {}},
        },
        {
            "name": "get_style_proposals",
            "description": "Get the list of style proposals and which one is selected.",
            "parameters": {"type": "OBJECT", "properties": {}},
        },
        # Navigation tools (always available)
        {
            "name": "next_stage",
            "description": "Advance to the next stage.",
            "parameters": {"type": "OBJECT", "properties": {}},
        },
        {
            "name": "back_stage",
            "description": "Go to the previous stage.",
            "parameters": {"type": "OBJECT", "properties": {}},
        },
        {
            "name": "go_to_stage",
            "description": "Jump to a specific stage (1-5).",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "stage": {
                        "type": "INTEGER",
                        "description": "Target stage number (1-5)",
                    }
                },
                "required": ["stage"],
            },
        },
    ]

    # Add stage-gated write tools
    declarations.extend(_get_write_tool_declarations(current_stage))
    return declarations


def _get_write_tool_declarations(current_stage: int) -> list:
    """Get write tool declarations for the current stage."""
    declarations = []
    allowed = STAGE_WRITE_TOOLS.get(current_stage, set())

    if "generate_slides" in allowed:
        declarations.append({
            "name": "generate_slides",
            "description": "Generate slide texts from the stored draft. Use this when the user wants to create or recreate all slides.",
            "parameters": {"type": "OBJECT", "properties": {}},
        })

    if "regenerate_slide" in allowed:
        declarations.append({
            "name": "regenerate_slide",
            "description": "Regenerate a single slide's text with an optional instruction describing what to change.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "slide_index": {
                        "type": "INTEGER",
                        "description": "1-based slide number",
                    },
                    "instruction": {
                        "type": "STRING",
                        "description": "What to change about the slide (e.g., 'make it less formal', 'add a question')",
                    },
                },
                "required": ["slide_index"],
            },
        })

    if "update_slide" in allowed:
        declarations.append({
            "name": "update_slide",
            "description": "Directly set a slide's title and/or body text.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "slide_index": {
                        "type": "INTEGER",
                        "description": "1-based slide number",
                    },
                    "title": {
                        "type": "STRING",
                        "description": "New title text (optional)",
                    },
                    "body": {
                        "type": "STRING",
                        "description": "New body text (optional)",
                    },
                },
                "required": ["slide_index"],
            },
        })

    if "generate_style_proposals" in allowed:
        declarations.append({
            "name": "generate_style_proposals",
            "description": "Generate visual style proposals with preview images.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "num_proposals": {
                        "type": "INTEGER",
                        "description": "Number of proposals to generate (default 3)",
                    },
                    "additional_instructions": {
                        "type": "STRING",
                        "description": "Style preferences (e.g., 'warm colors, minimalist')",
                    },
                },
            },
        })

    if "select_style_proposal" in allowed:
        declarations.append({
            "name": "select_style_proposal",
            "description": "Select a style proposal by its 1-based index.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "proposal_index": {
                        "type": "INTEGER",
                        "description": "1-based proposal number",
                    },
                },
                "required": ["proposal_index"],
            },
        })

    if "generate_prompts" in allowed:
        declarations.append({
            "name": "generate_prompts",
            "description": "Generate image prompts for all slides.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "style_instructions": {
                        "type": "STRING",
                        "description": "Additional style instructions for image prompts",
                    },
                },
            },
        })

    if "regenerate_prompt" in allowed:
        declarations.append({
            "name": "regenerate_prompt",
            "description": "Regenerate one slide's image prompt.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "slide_index": {
                        "type": "INTEGER",
                        "description": "1-based slide number",
                    },
                },
                "required": ["slide_index"],
            },
        })

    if "update_prompt" in allowed:
        declarations.append({
            "name": "update_prompt",
            "description": "Directly set a slide's image prompt text.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "slide_index": {
                        "type": "INTEGER",
                        "description": "1-based slide number",
                    },
                    "prompt": {
                        "type": "STRING",
                        "description": "The new image prompt text",
                    },
                },
                "required": ["slide_index", "prompt"],
            },
        })

    if "generate_images" in allowed:
        declarations.append({
            "name": "generate_images",
            "description": "Generate background images for all slides.",
            "parameters": {"type": "OBJECT", "properties": {}},
        })

    if "regenerate_image" in allowed:
        declarations.append({
            "name": "regenerate_image",
            "description": "Regenerate one slide's background image.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "slide_index": {
                        "type": "INTEGER",
                        "description": "1-based slide number",
                    },
                },
                "required": ["slide_index"],
            },
        })

    if "apply_styles" in allowed:
        declarations.append({
            "name": "apply_styles",
            "description": "Apply text styling/typography to all slide images.",
            "parameters": {"type": "OBJECT", "properties": {}},
        })

    if "update_style" in allowed:
        declarations.append({
            "name": "update_style",
            "description": "Update styling properties for one slide.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "slide_index": {
                        "type": "INTEGER",
                        "description": "1-based slide number",
                    },
                    "style": {
                        "type": "OBJECT",
                        "description": "Style properties to update (font_family, font_size_px, text_color, alignment, etc.)",
                    },
                },
                "required": ["slide_index"],
            },
        })

    if "export" in allowed:
        declarations.append({
            "name": "export",
            "description": "Export the carousel as a ZIP archive.",
            "parameters": {"type": "OBJECT", "properties": {}},
        })

    return declarations


class ChatService:
    """Agentic chat service with tool loop and SSE streaming."""

    def _parse_explicit_command(self, message: str) -> Tuple[Optional[str], Dict[str, Any]]:
        """Parse explicit slash commands (fast path, bypasses LLM)."""
        message = message.strip()
        for pattern, (tool, params_fn) in COMMAND_PATTERNS.items():
            match = re.match(pattern, message, re.IGNORECASE)
            if match:
                if callable(params_fn):
                    params = params_fn(match)
                else:
                    params = params_fn
                return tool, params
        return None, {}

    def _get_system_prompt(self, current_stage: int) -> str:
        """Get the agent system prompt with current stage info."""
        template = _load_prompt_file("chat_routing.prompt")
        return template.format(current_stage=current_stage)

    def _execute_read_tool(self, session_id: str, tool: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a read tool and return the result."""
        session = session_manager.get_session(session_id)
        if not session:
            return {"error": "No active session"}

        if tool == "get_slide":
            idx = params.get("slide_index", 1) - 1  # Convert 1-based to 0-based
            if idx < 0 or idx >= len(session.slides):
                return {"error": f"Slide index {idx + 1} out of range (1-{len(session.slides)})"}
            slide = session.slides[idx]
            return {
                "index": idx + 1,
                "title": slide.text.title,
                "body": slide.text.body,
                "image_prompt": slide.image_prompt,
                "has_image": slide.image_data is not None,
            }

        elif tool == "get_all_slides":
            return {
                "slides": [
                    {"index": i + 1, "title": s.text.title, "body": s.text.body}
                    for i, s in enumerate(session.slides)
                ]
            }

        elif tool == "get_draft":
            return {"draft_text": session.draft_text}

        elif tool == "get_session_info":
            return {
                "current_stage": session.current_stage,
                "num_slides": len(session.slides),
                "language": session.language,
                "shared_prompt_prefix": session.shared_prompt_prefix,
                "selected_style_index": session.selected_style_proposal_index,
            }

        elif tool == "get_style_proposals":
            return {
                "proposals": [
                    {"index": p.index + 1, "description": p.description}
                    for p in session.style_proposals
                ],
                "selected_index": (session.selected_style_proposal_index + 1)
                if session.selected_style_proposal_index is not None
                else None,
            }

        return {"error": f"Unknown read tool: {tool}"}

    async def _execute_write_tool(
        self, session_id: str, tool: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a write or navigation tool and return the result."""
        try:
            session = None

            if tool == "next_stage":
                session = session_manager.advance_stage(session_id)
                return {"success": True, "message": f"Advanced to Stage {session.current_stage}" if session else "Failed"}

            elif tool == "back_stage":
                session = session_manager.previous_stage(session_id)
                return {"success": True, "message": f"Returned to Stage {session.current_stage}" if session else "Failed"}

            elif tool == "go_to_stage":
                stage = params.get("stage", 1)
                session = session_manager.go_to_stage(session_id, stage)
                return {"success": True, "message": f"Now at Stage {stage}" if session else "Failed"}

            elif tool == "generate_slides":
                session = session_manager.get_session(session_id)
                if not session or not session.draft_text:
                    return {"success": False, "message": "No draft text available. Please enter a draft first."}
                session = await stage1_service.generate_slide_texts(
                    session_id, session.draft_text, session.num_slides,
                    session.include_titles, session.additional_instructions, session.language,
                )
                return {"success": True, "message": f"Generated {len(session.slides)} slides"}

            elif tool == "regenerate_slide":
                slide_index = params.get("slide_index", 1) - 1  # 1-based to 0-based
                instruction = params.get("instruction")
                session = await stage1_service.regenerate_slide_text(session_id, slide_index, instruction=instruction)
                return {"success": True, "message": f"Regenerated slide {slide_index + 1}"}

            elif tool == "update_slide":
                slide_index = params.get("slide_index", 1) - 1
                session = stage1_service.update_slide_text(
                    session_id, slide_index,
                    title=params.get("title"), body=params.get("body"),
                )
                return {"success": True, "message": f"Updated slide {slide_index + 1}"}

            elif tool == "generate_style_proposals":
                num = params.get("num_proposals", 3)
                instructions = params.get("additional_instructions")
                session = await stage_style_service.generate_proposals(
                    session_id, num_proposals=num, additional_instructions=instructions,
                )
                return {"success": True, "message": f"Generated {num} style proposals"}

            elif tool == "select_style_proposal":
                proposal_index = params.get("proposal_index", 1) - 1  # 1-based to 0-based
                session = stage_style_service.select_proposal(session_id, proposal_index)
                return {"success": True, "message": f"Selected style proposal {proposal_index + 1}"}

            elif tool == "generate_prompts":
                session = await stage2_service.generate_all_prompts(
                    session_id, image_style_instructions=params.get("style_instructions"),
                )
                return {"success": True, "message": "Generated image prompts for all slides"}

            elif tool == "regenerate_prompt":
                slide_index = params.get("slide_index", 1) - 1
                session = await stage2_service.regenerate_prompt(session_id, slide_index)
                return {"success": True, "message": f"Regenerated prompt for slide {slide_index + 1}"}

            elif tool == "update_prompt":
                slide_index = params.get("slide_index", 1) - 1
                session = stage2_service.update_prompt(session_id, slide_index, params.get("prompt", ""))
                return {"success": True, "message": f"Updated prompt for slide {slide_index + 1}"}

            elif tool == "generate_images":
                session = await stage3_service.generate_all_images(session_id)
                return {"success": True, "message": "Generated background images for all slides"}

            elif tool == "regenerate_image":
                slide_index = params.get("slide_index", 1) - 1
                session = await stage3_service.regenerate_image(session_id, slide_index)
                return {"success": True, "message": f"Regenerated image for slide {slide_index + 1}"}

            elif tool == "apply_styles":
                session = await stage4_service.apply_text_to_all_images(session_id)
                return {"success": True, "message": "Applied text styling to all slides"}

            elif tool == "update_style":
                slide_index = params.get("slide_index", 1) - 1
                style = params.get("style", {})
                session = stage4_service.update_style(session_id, slide_index, style)
                return {"success": True, "message": f"Updated style for slide {slide_index + 1}"}

            elif tool == "export":
                return {"success": True, "message": "Carousel is ready for export. The user can click the Export button to download."}

            else:
                return {"success": False, "message": f"Unknown tool: {tool}"}

        except Exception as e:
            logger.error(f"Tool execution error ({tool}): {e}")
            return {"success": False, "message": f"Error executing {tool}: {str(e)}"}

    async def _execute_tool(
        self, session_id: str, tool: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute any tool (read, write, or navigation)."""
        if tool in READ_TOOLS:
            return self._execute_read_tool(session_id, tool, params)
        else:
            return await self._execute_write_tool(session_id, tool, params)

    async def process_message_stream(
        self, session_id: str, message: str
    ) -> AsyncGenerator[str, None]:
        """Process a chat message via streaming agent loop, yielding SSE events."""
        session = session_manager.get_session(session_id)
        if not session:
            yield _sse_event("error", {"message": "No active session. Please start a new session first."})
            yield _sse_event("done", {"session": None, "has_writes": False})
            return

        current_stage = session.current_stage

        # Check for explicit slash commands (fast path)
        tool, params = self._parse_explicit_command(message)
        if tool:
            # Handle auto_generate mapping
            if tool == "auto_generate":
                stage_tools = {1: "generate_slides", 2: "generate_style_proposals", 3: "generate_prompts", 4: "generate_images", 5: "apply_styles"}
                tool = stage_tools.get(current_stage, tool)

            is_write = tool not in READ_TOOLS and tool not in NAV_TOOLS
            if is_write:
                session_manager.take_snapshot(session_id)

            yield _sse_event("tool_call", {"name": tool, "args": params})
            result = await self._execute_tool(session_id, tool, params)
            yield _sse_event("tool_result", {"name": tool, "result": result})

            session = session_manager.get_session(session_id)
            yield _sse_event("done", {
                "session": session.model_dump(mode="json") if session else None,
                "has_writes": is_write,
            })
            return

        # Agent loop with Gemini function calling
        has_writes = False
        snapshot_taken = False

        try:
            from google.genai import types

            tool_declarations = _get_tool_declarations(current_stage)
            tools = types.Tool(function_declarations=tool_declarations)
            config = types.GenerateContentConfig(
                tools=[tools],
                system_instruction=self._get_system_prompt(current_stage),
                temperature=1.0,
            )

            # Conversation contents for multi-turn
            contents = [
                types.Content(role="user", parts=[types.Part.from_text(text=message)])
            ]

            for _ in range(MAX_AGENT_ITERATIONS):
                # Check cancellation
                if _cancel_flags.pop(session_id, False):
                    yield _sse_event("error", {"message": "Stopped by user"})
                    break

                # Call Gemini with function declarations
                response = gemini_service.generate_with_tools(contents, config)

                if not response.candidates or not response.candidates[0].content.parts:
                    yield _sse_event("text", {"text": "I couldn't generate a response. Please try again."})
                    break

                # Process response parts
                function_calls = []
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "thought") and part.thought:
                        yield _sse_event("thinking", {"text": part.thought})
                    elif part.function_call:
                        function_calls.append(part.function_call)
                    elif part.text:
                        yield _sse_event("text", {"text": part.text})

                if not function_calls:
                    # No tool calls — LLM gave final text response, done
                    break

                # Append the model's response to conversation history
                contents.append(response.candidates[0].content)

                # Execute tool calls and collect results
                function_response_parts = []
                cancelled = False
                for fc in function_calls:
                    fc_args = dict(fc.args) if fc.args else {}
                    yield _sse_event("tool_call", {"name": fc.name, "args": fc_args})

                    # Check cancellation between tool executions
                    if _cancel_flags.pop(session_id, False):
                        yield _sse_event("error", {"message": "Stopped by user"})
                        cancelled = True
                        break

                    # Snapshot before first write tool
                    is_write = fc.name not in READ_TOOLS and fc.name not in NAV_TOOLS
                    if is_write and not snapshot_taken:
                        session_manager.take_snapshot(session_id)
                        snapshot_taken = True
                        has_writes = True

                    # Execute the tool
                    result = await self._execute_tool(session_id, fc.name, fc_args)
                    yield _sse_event("tool_result", {"name": fc.name, "result": result})

                    # Build function response part for next Gemini call
                    function_response_parts.append(
                        types.Part.from_function_response(
                            name=fc.name,
                            response={"result": result},
                        )
                    )

                if cancelled:
                    break

                # Append tool results to conversation for next iteration
                contents.append(types.Content(role="user", parts=function_response_parts))

        except GeminiError as e:
            yield _sse_event("error", {"message": str(e)})
        except Exception as e:
            logger.error(f"Agent loop error: {e}", exc_info=True)
            yield _sse_event("error", {"message": f"An error occurred: {str(e)}"})

        # Emit done with final session state
        session = session_manager.get_session(session_id)
        yield _sse_event("done", {
            "session": session.model_dump(mode="json") if session else None,
            "has_writes": has_writes,
        })

    async def process_message(
        self, session_id: str, message: str
    ) -> Dict[str, Any]:
        """Process a chat message (non-streaming, for backward compatibility and tests)."""
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

        # Handle auto_generate
        if tool == "auto_generate":
            stage_tools = {1: "generate_slides", 2: "generate_style_proposals", 3: "generate_prompts", 4: "generate_images", 5: "apply_styles"}
            tool = stage_tools.get(current_stage, tool)

        # Execute the tool
        result = await self._execute_tool(session_id, tool, params)

        session = session_manager.get_session(session_id)
        return {
            "success": result.get("success", True),
            "response": result.get("message") or response or f"Executed {tool}",
            "tool_called": tool,
            "session": session.model_dump() if session else None,
        }

    async def _route_with_llm(
        self, message: str, current_stage: int
    ) -> Tuple[Optional[str], Dict[str, Any], str]:
        """Fallback: single-shot JSON routing for backward compat."""
        prompt = f"""You are an AI assistant for Lucid, a carousel creation tool.
The user is in Stage {current_stage}.

User message: {message}

If this is a greeting or question, respond with:
{{"tool": null, "response": "your helpful response"}}

Otherwise respond with the appropriate tool call as JSON.
Respond with valid JSON only."""

        result = await gemini_service.generate_json(prompt)
        tool = result.get("tool")
        params = result.get("params", {})
        response = result.get("response", "I'll help you with that.")
        return tool, params, response


def cancel_agent(session_id: str) -> None:
    """Signal the agent loop to stop after the current step."""
    _cancel_flags[session_id] = True


# Global chat service instance
chat_service = ChatService()
