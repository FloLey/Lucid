"""Tests for font management."""

import pytest
from PIL import ImageFont

from app.services.font_manager import FontManager
from app.dependencies import container

font_manager = container.font_manager


class TestFontManager:
    """Tests for FontManager service."""

    def test_font_manager_init(self):
        """Test font manager initialization."""
        fm = FontManager()
        assert fm.get_font.cache_info().currsize == 0
        assert fm._available_fonts is None

    def test_weight_patterns_structure(self):
        """Test that weight patterns are correctly defined."""
        fm = FontManager()
        assert fm.WEIGHT_PATTERNS["regular"] == 400
        assert fm.WEIGHT_PATTERNS["bold"] == 700
        assert fm.WEIGHT_PATTERNS["thin"] == 100

    def test_parse_weight_from_filename(self):
        """Test parsing weight from font filenames."""
        fm = FontManager()
        assert fm._parse_weight_from_filename("Inter-Regular.ttf") == 400
        assert fm._parse_weight_from_filename("Inter-Bold.ttf") == 700
        assert fm._parse_weight_from_filename("Roboto-Light.ttf") == 300
        assert fm._parse_weight_from_filename("Font-500.ttf") == 500

    def test_parse_family_from_filename(self):
        """Test parsing family name from font filenames."""
        fm = FontManager()
        assert fm._parse_family_from_filename("Inter-Regular.ttf") == "Inter"
        assert fm._parse_family_from_filename("Roboto-Bold.ttf") == "Roboto"
        assert (
            fm._parse_family_from_filename("PlayfairDisplay-Regular.ttf")
            == "PlayfairDisplay"
        )

    def test_normalize_family_name(self):
        """Test family name normalization."""
        fm = FontManager()
        assert fm._normalize_family_name("inter") == "Inter"
        assert fm._normalize_family_name("playfair display") == "Playfair"
        assert fm._normalize_family_name("playfairdisplay") == "Playfair"

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
        assert fm.get_font.cache_info().currsize == 0

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

    def test_get_font_weights(self):
        """Test getting available weights for a family."""
        fm = FontManager()
        weights = fm.get_font_weights("Inter")
        assert isinstance(weights, list)
        # Should have at least default weight
        assert len(weights) >= 1

    def test_refresh(self):
        """Test refreshing the font index."""
        fm = FontManager()
        fm.get_available_fonts()
        fm.refresh()
        fonts_after = fm.get_available_fonts()
        # Should still work after refresh
        assert isinstance(fonts_after, list)

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
        assert isinstance(data["mappings"], dict)
