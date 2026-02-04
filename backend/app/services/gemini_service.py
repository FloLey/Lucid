"""Gemini AI service for text generation and routing."""

import json
import logging
from typing import Optional, Dict, Any

from app.config import GEMINI_API_KEY

logger = logging.getLogger(__name__)


class GeminiService:
    """Service for interacting with Google Gemini API."""

    def __init__(self):
        self._model = None
        self._configured = False
        self._genai = None

    def _try_import_genai(self):
        """Try to import google.generativeai, return None on failure."""
        if self._genai is not None:
            return self._genai

        try:
            import google.generativeai as genai
            self._genai = genai
            return genai
        except Exception as e:
            logger.warning(f"Cannot import google.generativeai: {e}")
            return None

    def _ensure_configured(self):
        """Ensure Gemini is configured."""
        if self._configured:
            return

        genai = self._try_import_genai()
        if genai and GEMINI_API_KEY:
            try:
                genai.configure(api_key=GEMINI_API_KEY)
                self._model = genai.GenerativeModel("gemini-1.5-flash")
                self._configured = True
            except Exception as e:
                logger.warning(f"Failed to configure Gemini: {e}")
        else:
            logger.info("Using mock responses (no API key or genai unavailable)")

    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
    ) -> str:
        """Generate text using Gemini."""
        self._ensure_configured()

        if not self._model:
            return self._mock_response(prompt)

        genai = self._try_import_genai()
        if not genai:
            return self._mock_response(prompt)

        try:
            generation_config = genai.GenerationConfig(
                temperature=temperature,
                max_output_tokens=4096,
            )

            if system_instruction:
                model = genai.GenerativeModel(
                    "gemini-1.5-flash",
                    system_instruction=system_instruction,
                )
            else:
                model = self._model

            response = model.generate_content(
                prompt,
                generation_config=generation_config,
            )
            return response.text

        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return self._mock_response(prompt)

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
            logger.error(f"JSON parse error: {e}, text: {text[:200]}")
            return {}

    def _mock_response(self, prompt: str) -> str:
        """Generate mock response for development."""
        if "slide" in prompt.lower():
            return json.dumps({
                "slides": [
                    {"title": "Introduction", "body": "Welcome to our presentation."},
                    {"title": "Key Point", "body": "Here's the main idea to understand."},
                    {"title": "Details", "body": "Let's dive deeper into the topic."},
                    {"title": "Benefits", "body": "Here's what you'll gain from this."},
                    {"title": "Call to Action", "body": "Take action now!"},
                ]
            })
        if "image prompt" in prompt.lower() or "visual" in prompt.lower():
            return json.dumps({
                "prompts": [
                    "A modern minimalist workspace with natural lighting",
                    "Abstract geometric shapes in warm colors",
                    "Professional business setting with clean lines",
                    "Inspirational nature scene with mountains",
                    "Dynamic action shot with motion blur",
                ]
            })
        if "style" in prompt.lower() or "typography" in prompt.lower():
            return json.dumps({
                "font_family": "Inter",
                "font_weight": 700,
                "font_size_px": 72,
                "text_color": "#FFFFFF",
                "alignment": "center",
                "box": {
                    "x_pct": 0.1,
                    "y_pct": 0.3,
                    "w_pct": 0.8,
                    "h_pct": 0.4,
                    "padding_pct": 0.05
                }
            })
        return "Mock response for: " + prompt[:100]


# Global Gemini service instance
gemini_service = GeminiService()
