"""Gemini AI service for text generation and routing (google.genai SDK)."""

import json
import logging
from typing import Optional, Dict, Any

from app.config import GOOGLE_API_KEY

logger = logging.getLogger(__name__)


class GeminiError(Exception):
    """Raised when Gemini is not available or a request fails."""
    pass


class GeminiService:
    """Service for interacting with Google Gemini API via google.genai."""

    def __init__(self):
        self._client = None
        self._configured = False

    def _ensure_configured(self):
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
                "google-genai package is not installed. "
                "Run: pip install google-genai"
            )
        except Exception as e:
            raise GeminiError(f"Failed to configure Gemini: {e}")

    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
    ) -> str:
        """Generate text using Gemini. Raises GeminiError on failure."""
        self._ensure_configured()

        try:
            from google.genai import types

            config = types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=4096,
                system_instruction=system_instruction,
            )

            response = self._client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[prompt],
                config=config,
            )
            return response.text

        except GeminiError:
            raise
        except Exception as e:
            raise GeminiError(f"Gemini API error: {e}")

    async def generate_json(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """Generate structured JSON output from Gemini."""
        json_prompt = f"{prompt}\n\nRespond with valid JSON only, no markdown."
        text = await self.generate_text(json_prompt, system_instruction, temperature)

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


# Global Gemini service instance
gemini_service = GeminiService()
