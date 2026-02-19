"""Font management service with fuzzy matching."""

import logging
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Union
from PIL import ImageFont

from app.config import FONTS_DIR

logger = logging.getLogger(__name__)


class FontManager:
    """
    Manages font loading with fuzzy matching support.

    Features:
    - Scans fonts directory at startup to build font index
    - Fuzzy weight matching (requests 600 but only 700 exists -> returns 700)
    - Only falls back to system fonts if fonts directory is empty
    """

    # Weight name mappings for parsing filenames
    WEIGHT_PATTERNS = {
        "thin": 100,
        "hairline": 100,
        "extralight": 200,
        "ultralight": 200,
        "light": 300,
        "regular": 400,
        "normal": 400,
        "medium": 500,
        "semibold": 600,
        "demibold": 600,
        "bold": 700,
        "extrabold": 800,
        "ultrabold": 800,
        "black": 900,
        "heavy": 900,
    }

    # Family name aliases for fuzzy matching
    FAMILY_ALIASES = {
        "playfair": "Playfair",
        "playfairdisplay": "Playfair",
        "playfair display": "Playfair",
        "inter": "Inter",
        "roboto": "Roboto",
        "montserrat": "Montserrat",
        "oswald": "Oswald",
        "opensans": "Open Sans",
        "open sans": "Open Sans",
    }

    # Fallback system fonts by platform
    SYSTEM_FALLBACKS = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "C:/Windows/Fonts/arial.ttf",
    ]

    def __init__(self) -> None:
        self._font_index: Dict[str, Dict[int, Path]] = {}
        self._available_fonts: Optional[List[str]] = None
        self._scan_fonts_directory()
        # Wrap the font loader with an LRU cache (per-instance, clearable)
        self.get_font = lru_cache(maxsize=128)(self._get_font_impl)

    def _parse_weight_from_filename(self, filename: str) -> int:
        """Extract font weight from filename using pattern matching."""
        name_lower = filename.lower()

        # Remove extension
        name_lower = re.sub(r"\.(ttf|otf|woff2?)$", "", name_lower)

        # Check for weight patterns
        for pattern, weight in self.WEIGHT_PATTERNS.items():
            if pattern in name_lower:
                return weight

        # Check for numeric weight (e.g., "Inter-400.ttf")
        numeric_match = re.search(r"[-_](\d{3})(?:[-_.]|$)", name_lower)
        if numeric_match:
            return int(numeric_match.group(1))

        # Default to regular weight
        return 400

    def _parse_family_from_filename(self, filename: str) -> str:
        """Extract font family from filename."""
        name = filename

        # Remove extension
        name = re.sub(r"\.(ttf|otf|woff2?)$", "", name)

        # Remove weight suffix patterns
        for pattern in self.WEIGHT_PATTERNS.keys():
            name = re.sub(rf"[-_]?{pattern}$", "", name, flags=re.IGNORECASE)

        # Remove numeric weight suffix
        name = re.sub(r"[-_]?\d{3}$", "", name)

        # Clean up remaining separators
        name = name.rstrip("-_")

        return name

    def _scan_fonts_directory(self) -> None:
        """Scan the fonts directory and build the font index."""
        self._font_index.clear()

        if not FONTS_DIR.exists():
            return

        # Scan for font files
        for font_file in FONTS_DIR.glob("*.ttf"):
            family = self._parse_family_from_filename(font_file.name)
            weight = self._parse_weight_from_filename(font_file.name)

            # Normalize family name
            normalized_family = self._normalize_family_name(family)

            if normalized_family not in self._font_index:
                self._font_index[normalized_family] = {}

            self._font_index[normalized_family][weight] = font_file

        # Also scan for OTF files
        for font_file in FONTS_DIR.glob("*.otf"):
            family = self._parse_family_from_filename(font_file.name)
            weight = self._parse_weight_from_filename(font_file.name)
            normalized_family = self._normalize_family_name(family)

            if normalized_family not in self._font_index:
                self._font_index[normalized_family] = {}

            # Only add if no TTF version exists for this weight
            if weight not in self._font_index[normalized_family]:
                self._font_index[normalized_family][weight] = font_file

    def _normalize_family_name(self, family: str) -> str:
        """Normalize a family name for consistent lookup."""
        lower = family.lower().replace(" ", "").replace("-", "")

        # Check aliases
        if lower in self.FAMILY_ALIASES:
            return self.FAMILY_ALIASES[lower]

        # Title case the original
        return family.replace("-", " ").title().replace(" ", "")

    def _find_closest_weight(self, family: str, target_weight: int) -> Optional[int]:
        """Find the closest available weight for a font family using fuzzy matching."""
        if family not in self._font_index:
            return None

        available_weights = list(self._font_index[family].keys())
        if not available_weights:
            return None

        # Find the closest weight
        return min(available_weights, key=lambda w: abs(w - target_weight))

    def _resolve_family(self, requested_family: str) -> Optional[str]:
        """Resolve a requested family name to an indexed family."""
        # Direct match
        if requested_family in self._font_index:
            return requested_family

        # Try normalized version
        normalized = self._normalize_family_name(requested_family)
        if normalized in self._font_index:
            return normalized

        # Try case-insensitive match
        lower = requested_family.lower()
        for indexed_family in self._font_index.keys():
            if indexed_family.lower() == lower:
                return indexed_family

        return None

    def _get_fallback_font_path(self) -> Optional[str]:
        """Get a system fallback font path."""
        for fallback in self.SYSTEM_FALLBACKS:
            if os.path.exists(fallback):
                return fallback
        return None

    def get_available_fonts(self) -> List[str]:
        """Get list of available font families."""
        if self._available_fonts is not None:
            return self._available_fonts

        available = list(self._font_index.keys())

        # If no fonts found, indicate system fallback
        if not available:
            available.append("System Default")

        self._available_fonts = sorted(available)
        return self._available_fonts

    def get_font_weights(self, family: str) -> List[int]:
        """Get available weights for a font family."""
        resolved = self._resolve_family(family)
        if resolved and resolved in self._font_index:
            return sorted(self._font_index[resolved].keys())
        return [400]  # Default weight

    def _get_font_impl(
        self, family: str, weight: int = 400, size: int = 72
    ) -> Union[ImageFont.FreeTypeFont, ImageFont.ImageFont]:
        """Load a PIL font with fuzzy family/weight matching.

        This method is wrapped by ``self.get_font`` which adds an LRU cache.
        If the exact weight isn't available, returns the closest available weight.
        Only falls back to system fonts if no fonts are indexed.
        """
        # Resolve family name
        resolved_family = self._resolve_family(family)

        if resolved_family:
            # Find closest weight
            closest_weight = self._find_closest_weight(resolved_family, weight)

            if closest_weight is not None:
                font_path = self._font_index[resolved_family][closest_weight]

                try:
                    return ImageFont.truetype(str(font_path), size)
                except Exception as e:
                    logger.warning(f"Failed to load font {font_path}: {e}")

        # Only fallback to system fonts if fonts directory is empty
        if not self._font_index:
            fallback_path = self._get_fallback_font_path()
            if fallback_path:
                try:
                    return ImageFont.truetype(fallback_path, size)
                except Exception:
                    pass

        # Ultimate fallback: PIL's default font
        default_font: Union[ImageFont.FreeTypeFont, ImageFont.ImageFont] = (
            ImageFont.load_default()
        )
        return default_font

    def refresh(self) -> None:
        """Refresh the font index by rescanning the directory."""
        self.get_font.cache_clear()
        self._available_fonts = None
        self._scan_fonts_directory()

    def clear_cache(self) -> None:
        """Clear the font cache."""
        self.get_font.cache_clear()
        self._available_fonts = None
