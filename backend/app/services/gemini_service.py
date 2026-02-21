"""Gemini AI service for text generation (google.genai SDK)."""

import json
import logging
from typing import List, Optional, Dict, Any

from app.config import GOOGLE_API_KEY, GEMINI_TEXT_MODEL
from app.services.llm_logger import log_llm_method

logger = logging.getLogger(__name__)


class GeminiError(Exception):
    """Raised when Gemini is not available or a request fails."""

    pass


class GeminiService:
    """Service for interacting with Google Gemini API via google.genai."""

    def __init__(self) -> None:
        self._client: Optional[Any] = None
        self._configured: bool = False

    def _ensure_configured(self) -> None:
        """Ensure Gemini is configured. Raises GeminiError if not possible."""
        if self._configured:
            return

        if not GOOGLE_API_KEY:
            raise GeminiError(
                "GOOGLE_API_KEY is not set. "
                "Set it in your environment variables to enable AI generation."
            )

        try:
            from google import genai

            self._client = genai.Client(api_key=GOOGLE_API_KEY)
            self._configured = True
        except ImportError:
            raise GeminiError(
                "google-genai package is not installed. Run: pip install google-genai"
            )
        except Exception as e:
            raise GeminiError(f"Failed to configure Gemini: {e}")

    @log_llm_method(
        method_name="generate_text",
        model=GEMINI_TEXT_MODEL,
        input_params=["prompt", "system_instruction", "temperature"],
        config_params=["temperature"],
    )
    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        caller: Optional[str] = None,
    ) -> str:
        """Generate text using Gemini. Raises GeminiError on failure."""
        self._ensure_configured()
        assert self._client is not None

        from google.genai import types

        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=65536,
            system_instruction=system_instruction,
        )

        response = self._client.models.generate_content(
            model=GEMINI_TEXT_MODEL,
            contents=[prompt],
            config=config,
        )
        return response.text

    async def generate_with_tools(
        self,
        contents: list,
        tools: list,
        system_instruction: str,
        temperature: float = 1.0,
    ) -> Any:
        """Generate content with function calling tools.

        Args:
            contents: List of content parts (messages/images).
            tools: List of tool definitions for function calling.
            system_instruction: System prompt to guide the model.
            temperature: Controls randomness (0.0 to 2.0).

        Returns:
            The raw Gemini response object for the caller to handle tool-call loops.
        """
        self._ensure_configured()
        assert self._client is not None
        from google.genai import types

        config = types.GenerateContentConfig(
            tools=tools,
            system_instruction=system_instruction,
            temperature=temperature,
        )
        return self._client.models.generate_content(
            model=GEMINI_TEXT_MODEL,
            contents=contents,
            config=config,
        )

    async def generate_chat_response(
        self,
        history: List[Dict[str, Any]],
        message: str,
        system_instruction: Optional[str] = None,
        use_search_grounding: bool = True,
        temperature: float = 1.0,
    ) -> tuple[str, bool]:
        """Send a message in a multi-turn chat, optionally grounded by Google Search.

        Args:
            history: Prior conversation turns as a list of
                     ``{"role": "user"|"model", "content": "..."}`` dicts.
            message: The new user message to send.
            system_instruction: Optional system-level instruction.
            use_search_grounding: If True, attach Google Search as a retrieval tool.
            temperature: Generation temperature.

        Returns:
            A tuple of (response_text, grounded) where grounded is True if Google
            Search was actually used to ground the response.
        """
        self._ensure_configured()
        assert self._client is not None

        from google.genai import types

        # Build the contents list from prior history + the new message
        contents: List[Any] = []
        for turn in history:
            role = turn.get("role", "user")
            content_text = turn.get("content", "")
            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part(text=content_text)],
                )
            )
        contents.append(
            types.Content(
                role="user",
                parts=[types.Part(text=message)],
            )
        )

        tools = []
        if use_search_grounding:
            tools.append(types.Tool(google_search=types.GoogleSearch()))

        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=8192,
            system_instruction=system_instruction,
            tools=tools if tools else None,
        )

        try:
            response = self._client.models.generate_content(
                model=GEMINI_TEXT_MODEL,
                contents=contents,
                config=config,
            )
            # Detect if Google Search was actually used by checking grounding_metadata
            grounded = (
                use_search_grounding
                and bool(response.candidates)
                and any(
                    getattr(c, "grounding_metadata", None) is not None
                    for c in response.candidates
                )
            )
            return response.text or "", grounded
        except Exception as e:
            raise GeminiError(f"Chat generation failed: {e}")

    async def generate_json(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        caller: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate structured JSON output from Gemini.

        Args:
            prompt: The user prompt.
            system_instruction: Optional system level instructions.
            temperature: Generation temperature.
            caller: Identifier for logging purposes.

        Returns:
            A dictionary parsed from the AI's JSON response.
        """
        json_prompt = f"{prompt}\n\nRespond with valid JSON only, no markdown."
        text = await self.generate_text(
            json_prompt, system_instruction, temperature, caller=caller
        )

        # Clean up response
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise GeminiError(f"Failed to parse AI response as JSON: {e}")
