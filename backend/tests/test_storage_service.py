"""Tests for StorageService — save, read, delete, encode/decode, security."""

import base64
import asyncio
import os
from pathlib import Path

import pytest
from PIL import Image
from io import BytesIO

from app.services.storage_service import StorageService, _IMAGE_URL_PREFIX
from tests.conftest import run_async


def _tiny_png_b64() -> str:
    """Return a minimal valid 1x1 white PNG as a base64 string."""
    img = Image.new("RGB", (1, 1), color=(255, 255, 255))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


@pytest.fixture
def storage(tmp_path, monkeypatch):
    """Return a StorageService instance that writes to a temp directory."""
    import app.services.storage_service as ss_module

    # Patch IMAGE_DIR in the module so our service uses the temp dir
    monkeypatch.setattr(ss_module, "IMAGE_DIR", tmp_path)
    svc = StorageService()
    return svc, tmp_path


class TestSaveImageToDisk:
    def test_returns_url_path(self, storage):
        svc, _ = storage
        b64 = _tiny_png_b64()
        path = run_async(svc.save_image_to_disk(b64))
        assert path.startswith(_IMAGE_URL_PREFIX)
        assert path.endswith(".png")

    def test_file_exists_on_disk(self, storage):
        svc, tmp_path = storage
        b64 = _tiny_png_b64()
        url = run_async(svc.save_image_to_disk(b64))
        filename = url[len(_IMAGE_URL_PREFIX):]
        assert (tmp_path / filename).exists()

    def test_file_content_matches(self, storage):
        svc, tmp_path = storage
        raw_bytes = base64.b64decode(_tiny_png_b64())
        url = run_async(svc.save_image_to_disk(base64.b64encode(raw_bytes).decode()))
        filename = url[len(_IMAGE_URL_PREFIX):]
        assert (tmp_path / filename).read_bytes() == raw_bytes

    def test_each_call_creates_unique_file(self, storage):
        svc, tmp_path = storage
        b64 = _tiny_png_b64()
        url1 = run_async(svc.save_image_to_disk(b64))
        url2 = run_async(svc.save_image_to_disk(b64))
        assert url1 != url2


class TestDeleteImage:
    def test_deletes_existing_file(self, storage):
        svc, tmp_path = storage
        url = run_async(svc.save_image_to_disk(_tiny_png_b64()))
        filename = url[len(_IMAGE_URL_PREFIX):]
        assert (tmp_path / filename).exists()
        run_async(svc.delete_image(url))
        assert not (tmp_path / filename).exists()

    def test_delete_none_is_noop(self, storage):
        svc, _ = storage
        # Must not raise
        run_async(svc.delete_image(None))

    def test_delete_b64_string_is_noop(self, storage):
        svc, _ = storage
        # Raw base64 does not look like /images/ — must be ignored silently
        run_async(svc.delete_image(_tiny_png_b64()))

    def test_delete_missing_file_is_noop(self, storage):
        svc, _ = storage
        # File that was never created
        run_async(svc.delete_image(f"{_IMAGE_URL_PREFIX}ghost.png"))


class TestReadImageBytes:
    def test_reads_stored_file(self, storage):
        svc, _ = storage
        raw = base64.b64decode(_tiny_png_b64())
        url = run_async(svc.save_image_to_disk(base64.b64encode(raw).decode()))
        assert svc.read_image_bytes(url) == raw

    def test_reads_raw_base64(self, storage):
        svc, _ = storage
        b64 = _tiny_png_b64()
        assert svc.read_image_bytes(b64) == base64.b64decode(b64)

    def test_path_traversal_raises(self, storage):
        svc, _ = storage
        with pytest.raises(ValueError):
            svc.read_image_bytes(f"{_IMAGE_URL_PREFIX}../../../etc/passwd")


class TestEncodeDecodeRoundtrip:
    def test_encode_decode_roundtrip(self, storage):
        svc, _ = storage
        original = Image.new("RGB", (4, 4), color=(100, 150, 200))
        b64 = svc.encode_image(original)
        recovered = svc.decode_image_from_path_or_b64(b64)
        assert recovered.size == original.size

    def test_decode_from_stored_path(self, storage):
        svc, _ = storage
        b64 = _tiny_png_b64()
        url = run_async(svc.save_image_to_disk(b64))
        img = svc.decode_image_from_path_or_b64(url)
        assert img.size == (1, 1)
