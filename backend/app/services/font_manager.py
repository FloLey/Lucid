"""Font management service."""

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from PIL import ImageFont

from app.config import FONTS_DIR


class FontManager:
    """Manages font loading and mapping for PIL rendering."""

    # Mapping of font family names to their file patterns
    FONT_MAPPINGS: Dict[str, Dict[int, str]] = {
        "Inter": {
            400: "Inter-Regular.ttf",
            500: "Inter-Medium.ttf",
            600: "Inter-SemiBold.ttf",
            700: "Inter-Bold.ttf",
        },
        "Roboto": {
            400: "Roboto-Regular.ttf",
            500: "Roboto-Medium.ttf",
            700: "Roboto-Bold.ttf",
        },
        "Open Sans": {
            400: "OpenSans-Regular.ttf",
            600: "OpenSans-SemiBold.ttf",
            700: "OpenSans-Bold.ttf",
        },
        "Montserrat": {
            400: "Montserrat-Regular.ttf",
            500: "Montserrat-Medium.ttf",
            600: "Montserrat-SemiBold.ttf",
            700: "Montserrat-Bold.ttf",
        },
        "Lato": {
            400: "Lato-Regular.ttf",
            700: "Lato-Bold.ttf",
            900: "Lato-Black.ttf",
        },
        "Oswald": {
            400: "Oswald-Regular.ttf",
            500: "Oswald-Medium.ttf",
            600: "Oswald-SemiBold.ttf",
            700: "Oswald-Bold.ttf",
        },
        "Playfair Display": {
            400: "PlayfairDisplay-Regular.ttf",
            500: "PlayfairDisplay-Medium.ttf",
            600: "PlayfairDisplay-SemiBold.ttf",
            700: "PlayfairDisplay-Bold.ttf",
        },
        "Raleway": {
            400: "Raleway-Regular.ttf",
            500: "Raleway-Medium.ttf",
            600: "Raleway-SemiBold.ttf",
            700: "Raleway-Bold.ttf",
        },
        "Poppins": {
            400: "Poppins-Regular.ttf",
            500: "Poppins-Medium.ttf",
            600: "Poppins-SemiBold.ttf",
            700: "Poppins-Bold.ttf",
        },
        "Bebas Neue": {
            400: "BebasNeue-Regular.ttf",
        },
    }

    # Fallback system fonts by platform
    SYSTEM_FALLBACKS = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",  # Linux
        "/System/Library/Fonts/Helvetica.ttc",  # macOS
        "C:/Windows/Fonts/arial.ttf",  # Windows
    ]

    def __init__(self):
        self._font_cache: Dict[Tuple[str, int, int], ImageFont.FreeTypeFont] = {}
        self._available_fonts: Optional[List[str]] = None

    def get_available_fonts(self) -> List[str]:
        """Get list of available font families."""
        if self._available_fonts is not None:
            return self._available_fonts

        available = []
        for family, weights in self.FONT_MAPPINGS.items():
            for weight, filename in weights.items():
                font_path = FONTS_DIR / filename
                if font_path.exists():
                    if family not in available:
                        available.append(family)
                    break

        # Always include a fallback option
        if not available:
            available.append("System Default")

        self._available_fonts = available
        return available

    def _find_closest_weight(self, family: str, target_weight: int) -> int:
        """Find the closest available weight for a font family."""
        if family not in self.FONT_MAPPINGS:
            return 400

        weights = list(self.FONT_MAPPINGS[family].keys())
        return min(weights, key=lambda w: abs(w - target_weight))

    def _get_font_path(self, family: str, weight: int) -> Optional[Path]:
        """Get the file path for a font."""
        if family not in self.FONT_MAPPINGS:
            return None

        closest_weight = self._find_closest_weight(family, weight)
        filename = self.FONT_MAPPINGS[family][closest_weight]
        font_path = FONTS_DIR / filename

        if font_path.exists():
            return font_path
        return None

    def _get_fallback_font_path(self) -> Optional[str]:
        """Get a system fallback font path."""
        for fallback in self.SYSTEM_FALLBACKS:
            if os.path.exists(fallback):
                return fallback
        return None

    def get_font(
        self, family: str, weight: int = 400, size: int = 72
    ) -> ImageFont.FreeTypeFont:
        """Get a PIL font object."""
        cache_key = (family, weight, size)

        if cache_key in self._font_cache:
            return self._font_cache[cache_key]

        # Try to load the requested font
        font_path = self._get_font_path(family, weight)

        if font_path:
            try:
                font = ImageFont.truetype(str(font_path), size)
                self._font_cache[cache_key] = font
                return font
            except Exception:
                pass

        # Try system fallback
        fallback_path = self._get_fallback_font_path()
        if fallback_path:
            try:
                font = ImageFont.truetype(fallback_path, size)
                self._font_cache[cache_key] = font
                return font
            except Exception:
                pass

        # Ultimate fallback: PIL's default font (scaled by repetition for size)
        font = ImageFont.load_default()
        return font

    def clear_cache(self):
        """Clear the font cache."""
        self._font_cache.clear()
        self._available_fonts = None


# Global font manager instance
font_manager = FontManager()
