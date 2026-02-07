"""Application configuration."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables (check project root .env first, then backend/.env)
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
FONTS_DIR = BASE_DIR / "fonts"
OUTPUT_DIR = BASE_DIR / "output"

# Ensure output directory exists
OUTPUT_DIR.mkdir(exist_ok=True)

# API Keys
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

# Image settings
IMAGE_WIDTH = 1080
IMAGE_HEIGHT = 1350
IMAGE_ASPECT_RATIO = "4:5"

# Logging
LOG_FILE = BASE_DIR / "lucid.log"
