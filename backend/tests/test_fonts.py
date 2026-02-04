"""Tests for font management."""

import pytest
from PIL import ImageFont

from app.services.font_manager import FontManager, font_manager


class TestFontManager:
    """Tests for FontManager service."""

    def test_font_manager_init(self):
        """Test font manager initialization."""
        fm = FontManager()
        assert fm._font_cache == {}
        assert fm._available_fonts is None

    def test_font_mappings_structure(self):
        """Test that font mappings have correct structure."""
        fm = FontManager()
        for family, weights in fm.FONT_MAPPINGS.items():
            assert isinstance(family, str)
            assert isinstance(weights, dict)
            for weight, filename in weights.items():
                assert isinstance(weight, int)
                assert isinstance(filename, str)
                assert filename.endswith((".ttf", ".otf"))

    def test_find_closest_weight(self):
        """Test finding closest available weight."""
        fm = FontManager()
        # Inter has weights: 400, 500, 600, 700
        assert fm._find_closest_weight("Inter", 400) == 400
        assert fm._find_closest_weight("Inter", 700) == 700
        assert fm._find_closest_weight("Inter", 450) == 400  # Closer to 400
        assert fm._find_closest_weight("Inter", 650) == 600  # Closer to 600
        assert fm._find_closest_weight("Inter", 800) == 700  # Beyond max

    def test_find_closest_weight_unknown_family(self):
        """Test fallback for unknown font family."""
        fm = FontManager()
        assert fm._find_closest_weight("Unknown Font", 700) == 400

    def test_get_available_fonts_returns_list(self):
        """Test that get_available_fonts returns a list."""
        fm = FontManager()
        fonts = fm.get_available_fonts()
        assert isinstance(fonts, list)
        # Should have at least a fallback
        assert len(fonts) >= 1

    def test_get_available_fonts_caching(self):
        """Test that available fonts are cached."""
        fm = FontManager()
        fonts1 = fm.get_available_fonts()
        fonts2 = fm.get_available_fonts()
        assert fonts1 is fonts2  # Same object (cached)

    def test_clear_cache(self):
        """Test cache clearing."""
        fm = FontManager()
        fm.get_available_fonts()
        assert fm._available_fonts is not None
        fm.clear_cache()
        assert fm._available_fonts is None
        assert fm._font_cache == {}

    def test_get_font_returns_font(self):
        """Test that get_font returns a font object."""
        fm = FontManager()
        font = fm.get_font("Inter", 700, 48)
        # Should return some kind of font (either custom or fallback)
        assert font is not None

    def test_get_font_caching(self):
        """Test that fonts are cached."""
        fm = FontManager()
        font1 = fm.get_font("Roboto", 400, 36)
        font2 = fm.get_font("Roboto", 400, 36)
        # If it's a FreeTypeFont, it should be the same cached object
        # Default font may not be cached the same way
        if isinstance(font1, ImageFont.FreeTypeFont):
            assert font1 is font2

    def test_global_font_manager(self):
        """Test the global font manager instance."""
        assert font_manager is not None
        assert isinstance(font_manager, FontManager)


class TestFontRoutes:
    """Tests for font API routes."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        from fastapi.testclient import TestClient
        from app.main import app
        return TestClient(app)

    def test_list_fonts(self, client):
        """Test listing available fonts."""
        response = client.get("/api/fonts/")
        assert response.status_code == 200
        data = response.json()
        assert "fonts" in data
        assert isinstance(data["fonts"], list)

    def test_get_font_mappings(self, client):
        """Test getting font mappings."""
        response = client.get("/api/fonts/mappings")
        assert response.status_code == 200
        data = response.json()
        assert "mappings" in data
        assert "Inter" in data["mappings"]
        assert "Roboto" in data["mappings"]
