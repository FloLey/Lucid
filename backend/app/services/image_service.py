"""Image generation service using Gemini Image API."""

import base64
import logging
from io import BytesIO
from typing import Optional

from PIL import Image

from app.config import GEMINI_API_KEY, IMAGE_WIDTH, IMAGE_HEIGHT

logger = logging.getLogger(__name__)


class ImageService:
    """Service for generating images using Gemini Image API."""

    def __init__(self):
        self._model = None
        self._configured = False

    def _ensure_configured(self):
        """Ensure Gemini Image API is configured."""
        if self._configured:
            return

        try:
            import google.generativeai as genai

            if GEMINI_API_KEY:
                genai.configure(api_key=GEMINI_API_KEY)
                # Use Gemini 2.5 Flash Image for generation (2026 standard)
                self._model = genai.ImageGenerationModel("gemini-2.5-flash-image")
                self._configured = True
            else:
                logger.info("No API key, using placeholder images")
        except Exception as e:
            logger.warning(f"Cannot configure Gemini Image API: {e}")

    async def generate_image(self, prompt: str) -> str:
        """Generate an image from a prompt, return as base64."""
        self._ensure_configured()

        if self._model:
            try:
                # Add constraints to prompt
                full_prompt = f"{prompt}. Aspect ratio 4:5 (vertical). No text or words in the image. High quality, suitable for social media carousel background."

                response = self._model.generate_images(
                    prompt=full_prompt,
                    number_of_images=1,
                    aspect_ratio="4:5",
                )

                if response.images:
                    # Get the generated image
                    image_bytes = response.images[0]._pil_image
                    # Resize to exact dimensions
                    image = image_bytes.resize((IMAGE_WIDTH, IMAGE_HEIGHT), Image.Resampling.LANCZOS)
                    # Convert to base64
                    buffer = BytesIO()
                    image.save(buffer, format="PNG")
                    return base64.b64encode(buffer.getvalue()).decode("utf-8")

            except Exception as e:
                logger.error(f"Image generation failed: {e}")

        # Return placeholder image
        return self._generate_placeholder(prompt)

    def _generate_placeholder(self, prompt: str) -> str:
        """Generate a placeholder gradient image."""
        from PIL import ImageDraw, ImageFont

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
