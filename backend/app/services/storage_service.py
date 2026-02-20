"""Local disk storage service for image files.

Separates filesystem I/O from AI generation logic, following the
Single Responsibility Principle. All reads/writes to the image directory
go through this service.
"""

import base64
import logging
import os
import uuid
from io import BytesIO
from pathlib import Path
from typing import Optional

from PIL import Image

logger = logging.getLogger(__name__)

# Directory where generated images are written to disk.
# Override with LUCID_IMAGE_DIR for tests or alternative deployments.
IMAGE_DIR: Path = Path(os.getenv("LUCID_IMAGE_DIR", "/app/data/images"))

# URL prefix served by the static-files mount in main.py
_IMAGE_URL_PREFIX = "/images/"


def _is_file_path(value: str) -> bool:
    """Return True if *value* looks like an /images/ URL path rather than base64."""
    return value.startswith(_IMAGE_URL_PREFIX)


class StorageService:
    """Service for local disk I/O of image files.

    Responsibilities:
    - Saving base64-encoded PNGs to the image directory
    - Reading image bytes from either a URL path or a raw base64 string
    - Decoding stored images into PIL objects
    - Deleting orphaned image files from disk
    """

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

    def encode_image(self, image: Image.Image) -> str:
        """Encode a PIL Image to a base64 PNG string."""
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    def delete_image(self, path_or_b64: Optional[str]) -> None:
        """Delete an image file from disk if *path_or_b64* is a stored file path.

        Silently ignores raw base64 strings and missing files.
        """
        if not path_or_b64 or not _is_file_path(path_or_b64):
            return
        file_name = path_or_b64[len(_IMAGE_URL_PREFIX):]
        file_path = IMAGE_DIR / file_name
        try:
            file_path.unlink(missing_ok=True)
        except Exception as e:
            logger.warning("Failed to delete image file %s: %s", file_path, e)


# Module-level singleton
storage_service = StorageService()
