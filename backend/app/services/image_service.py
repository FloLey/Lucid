"""Image generation service using Gemini Nano Banana (google.genai)."""

import base64
import logging
import os
import uuid
from io import BytesIO
from pathlib import Path

from PIL import Image

from app.config import GOOGLE_API_KEY, IMAGE_WIDTH, IMAGE_HEIGHT, GEMINI_IMAGE_MODEL
from app.services.llm_logger import log_llm_method

logger = logging.getLogger(__name__)

# Directory where generated images are written to disk.
# Override with LUCID_IMAGE_DIR for tests or alternative deployments.
IMAGE_DIR: Path = Path(os.getenv("LUCID_IMAGE_DIR", "/app/data/images"))

# URL prefix served by the static-files mount in main.py
_IMAGE_URL_PREFIX = "/images/"


def _is_file_path(value: str) -> bool:
    """Return True if *value* looks like an /images/ URL path rather than base64."""
    return value.startswith(_IMAGE_URL_PREFIX)


class ImageService:
    """Service for generating images using Gemini's native image generation."""

    def __init__(self):
        self._client = None
        self._configured = False

    def _ensure_configured(self):
        """Verify and initialize the Gemini client if an API key is available."""
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

    @log_llm_method(
        method_name="generate_image",
        model=GEMINI_IMAGE_MODEL,
        input_params=["prompt"],
        config_params=[],
    )
    async def generate_image(self, prompt: str) -> str:
        """Generate an image from a prompt, return as base64."""
        self._ensure_configured()

        if not self._client:
            # No API key configured — return placeholder
            return self._generate_placeholder(prompt)

        from google.genai import types

        full_prompt = (
            f"{prompt}. Aspect ratio 4:5 (vertical). "
            "No text or words in the image. "
            "High quality, suitable for social media carousel background."
        )

        response = self._client.models.generate_content(
            model=GEMINI_IMAGE_MODEL,
            contents=[full_prompt],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            ),
        )

        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                # Decode the image bytes
                image_bytes = part.inline_data.data
                image: Image.Image = Image.open(BytesIO(image_bytes))
                # Resize to exact dimensions
                image = image.resize(
                    (IMAGE_WIDTH, IMAGE_HEIGHT), Image.Resampling.LANCZOS
                )
                buffer = BytesIO()
                image.save(buffer, format="PNG")
                return base64.b64encode(buffer.getvalue()).decode("utf-8")

        raise Exception("No image returned in response")

    def save_image_to_disk(self, base64_data: str) -> str:
        """Save a base64-encoded PNG to the image directory.

        Returns the URL path (e.g. ``/images/<uuid>.png``) that should be
        stored in the database instead of the raw base64 blob.
        """
        IMAGE_DIR.mkdir(parents=True, exist_ok=True)
        file_name = f"{uuid.uuid4()}.png"
        file_path = IMAGE_DIR / file_name
        file_path.write_bytes(base64.b64decode(base64_data))
        return f"{_IMAGE_URL_PREFIX}{file_name}"

    def read_image_bytes(self, path_or_b64: str) -> bytes:
        """Return raw PNG bytes from either an /images/ path or a base64 string."""
        if _is_file_path(path_or_b64):
            file_name = path_or_b64[len(_IMAGE_URL_PREFIX):]
            return (IMAGE_DIR / file_name).read_bytes()
        return base64.b64decode(path_or_b64)

    def decode_image_from_path_or_b64(self, data: str) -> Image.Image:
        """Return a PIL Image from either an /images/ path or a base64 string."""
        return Image.open(BytesIO(self.read_image_bytes(data)))

    def _generate_placeholder(self, prompt: str) -> str:
        """Generate a placeholder gradient image."""
        from PIL import ImageDraw

        # Create gradient background
        image = Image.new("RGB", (IMAGE_WIDTH, IMAGE_HEIGHT))
        pixels = image.load()
        assert pixels is not None

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
                    r, g, b = int((c + m) * 255), int((x_val + m) * 255), int(m * 255)
                elif hue_section < 2:
                    r, g, b = int((x_val + m) * 255), int((c + m) * 255), int(m * 255)
                elif hue_section < 3:
                    r, g, b = int(m * 255), int((c + m) * 255), int((x_val + m) * 255)
                elif hue_section < 4:
                    r, g, b = int(m * 255), int((x_val + m) * 255), int((c + m) * 255)
                elif hue_section < 5:
                    r, g, b = int((x_val + m) * 255), int(m * 255), int((c + m) * 255)
                else:
                    r, g, b = int((c + m) * 255), int(m * 255), int((x_val + m) * 255)

                pixels[x, y] = (r, g, b)

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
        """Decode a base64 image string to a PIL Image object.

        Args:
            base64_data: The base64 encoded image string.

        Returns:
            A PIL Image object.
        """
        image_bytes = base64.b64decode(base64_data)
        return Image.open(BytesIO(image_bytes))

    def encode_image(self, image: Image.Image) -> str:
        """Encode a PIL Image object to a base64 string.

        Args:
            image: The PIL Image object to encode.

        Returns:
            A base64 encoded string of the image in PNG format.
        """
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
