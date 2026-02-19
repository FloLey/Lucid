"""Application configuration."""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables (check project root .env first, then backend/.env)
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
FONTS_DIR = BASE_DIR / "fonts"
OUTPUT_DIR = BASE_DIR / "output"

# Ensure output directory exists
try:
    OUTPUT_DIR.mkdir(exist_ok=True)
except PermissionError:
    logger.warning(
        f"Permission denied creating output directory {OUTPUT_DIR}. Falling back to /tmp/lucid_output"
    )
    # Fall back to temporary directory
    OUTPUT_DIR = Path("/tmp/lucid_output")
    try:
        OUTPUT_DIR.mkdir(exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to create fallback output directory {OUTPUT_DIR}: {e}")
        raise

# API Keys
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

# Image settings (default source of truth — can be overridden by config.json)
IMAGE_WIDTH = 1080
IMAGE_HEIGHT = 1350
IMAGE_ASPECT_RATIO = "4:5"

# Gemini model names
GEMINI_TEXT_MODEL = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.5-flash")
GEMINI_IMAGE_MODEL = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")

# Logging
LOG_FILE = BASE_DIR / "lucid.log"
