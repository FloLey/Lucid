"""Image generation service using Gemini Nano Banana (google.genai)."""

import base64
import logging
from io import BytesIO
from typing import Optional

from PIL import Image

from app.config import GOOGLE_API_KEY, IMAGE_WIDTH, IMAGE_HEIGHT

logger = logging.getLogger(__name__)


class ImageService:
    """Service for generating images using Gemini's native image generation."""

    def __init__(self):
        self._client = None
        self._configured = False

    def _ensure_configured(self):
        """Ensure google.genai client is configured."""
        if self._configured:
            return

        try:
            from google import genai

            if GOOGLE_API_KEY:
                self._client = genai.Client(api_key=GOOGLE_API_KEY)
                self._configured = True
            else:
                logger.info("No API key, using placeholder images")
        except Exception as e:
            logger.warning(f"Cannot configure google.genai: {e}")

    async def generate_image(self, prompt: str) -> str:
        """Generate an image from a prompt, return as base64."""
        self._ensure_configured()

        if self._client:
            try:
                from google.genai import types

                full_prompt = (
                    f"{prompt}. Aspect ratio 4:5 (vertical). "
                    "No text or words in the image. "
                    "High quality, suitable for social media carousel background."
                )

                response = self._client.models.generate_content(
                    model="gemini-2.5-flash-image",
                    contents=[full_prompt],
                    config=types.GenerateContentConfig(
                        response_modalities=["IMAGE"],
                    ),
                )

                for part in response.candidates[0].content.parts:
                    if part.inline_data is not None:
                        # Decode the image bytes
                        image_bytes = part.inline_data.data
                        image = Image.open(BytesIO(image_bytes))
                        # Resize to exact dimensions
                        image = image.resize(
                            (IMAGE_WIDTH, IMAGE_HEIGHT), Image.Resampling.LANCZOS
                        )
                        buffer = BytesIO()
                        image.save(buffer, format="PNG")
                        return base64.b64encode(buffer.getvalue()).decode("utf-8")

                raise Exception("No image returned in response")

            except Exception as e:
                logger.error(f"Image generation failed: {e}")
                raise Exception(f"Image generation failed: {e}")

        # No API key configured — return placeholder
        return self._generate_placeholder(prompt)

    def _generate_placeholder(self, prompt: str) -> str:
        """Generate a placeholder gradient image."""
        from PIL import ImageDraw

        # Create gradient background
        image = Image.new("RGB", (IMAGE_WIDTH, IMAGE_HEIGHT))
        pixels = image.load()

        # Simple gradient based on prompt hash for variety
        prompt_hash = hash(prompt) % 360
        for y in range(IMAGE_HEIGHT):
            for x in range(IMAGE_WIDTH):
                # Create HSV-like gradient
                h = (prompt_hash + x // 10) % 360
                s = 0.3 + 0.3 * (y / IMAGE_HEIGHT)
                v = 0.6 + 0.2 * (1 - y / IMAGE_HEIGHT)

                # HSV to RGB (simplified)
                c = v * s
                hue_section = h / 60
                x_val = c * (1 - abs(hue_section % 2 - 1))
                m = v - c

                if hue_section < 1:
                    r, g, b = c, x_val, 0
                elif hue_section < 2:
                    r, g, b = x_val, c, 0
                elif hue_section < 3:
                    r, g, b = 0, c, x_val
                elif hue_section < 4:
                    r, g, b = 0, x_val, c
                elif hue_section < 5:
                    r, g, b = x_val, 0, c
                else:
                    r, g, b = c, 0, x_val

                pixels[x, y] = (
                    int((r + m) * 255),
                    int((g + m) * 255),
                    int((b + m) * 255),
                )

        # Add "PLACEHOLDER" text
        draw = ImageDraw.Draw(image)
        draw.text(
            (IMAGE_WIDTH // 2, IMAGE_HEIGHT // 2),
            "PLACEHOLDER",
            fill=(255, 255, 255, 180),
            anchor="mm",
        )

        # Convert to base64
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    def decode_image(self, base64_data: str) -> Image.Image:
        """Decode a base64 image to PIL Image."""
        image_bytes = base64.b64decode(base64_data)
        return Image.open(BytesIO(image_bytes))

    def encode_image(self, image: Image.Image) -> str:
        """Encode a PIL Image to base64."""
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")


# Global image service instance
image_service = ImageService()
