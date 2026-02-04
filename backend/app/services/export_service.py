"""Export service for generating ZIP archives of carousel slides."""

import base64
import json
import logging
import re
import zipfile
from datetime import datetime
from io import BytesIO
from typing import Optional

from app.models.session import SessionState
from app.services.session_manager import session_manager

logger = logging.getLogger(__name__)


class ExportService:
    """Service for exporting carousel slides as ZIP archives."""

    def _sanitize_filename(self, text: str, max_length: int = 30) -> str:
        """Sanitize text for use in filename."""
        # Remove special characters
        text = re.sub(r"[^\w\s-]", "", text)
        # Replace spaces with underscores
        text = re.sub(r"\s+", "_", text)
        # Truncate
        return text[:max_length].strip("_")

    def _generate_filename(self, index: int, title: Optional[str]) -> str:
        """Generate filename for a slide."""
        prefix = f"{index + 1:02d}"
        if title:
            sanitized = self._sanitize_filename(title)
            if sanitized:
                return f"{prefix}_{sanitized}.png"
        return f"{prefix}_slide.png"

    def _generate_metadata(self, session: SessionState) -> dict:
        """Generate metadata for the export."""
        slides_meta = []
        for slide in session.slides:
            slides_meta.append({
                "index": slide.index,
                "title": slide.text.title,
                "body": slide.text.body,
                "image_prompt": slide.image_prompt,
                "style": slide.style.model_dump(),
            })

        return {
            "session_id": session.session_id,
            "created_at": session.created_at.isoformat(),
            "exported_at": datetime.utcnow().isoformat(),
            "num_slides": len(session.slides),
            "draft_text": session.draft_text,
            "image_style_instructions": session.image_style_instructions,
            "slides": slides_meta,
        }

    def export_session(self, session_id: str) -> Optional[BytesIO]:
        """Export session slides as ZIP archive."""
        session = session_manager.get_session(session_id)
        if not session or not session.slides:
            return None

        # Create ZIP in memory
        zip_buffer = BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            # Add final images
            for slide in session.slides:
                image_data = slide.final_image or slide.image_data
                if not image_data:
                    continue

                filename = self._generate_filename(slide.index, slide.text.title)

                # Decode base64 and add to ZIP
                try:
                    image_bytes = base64.b64decode(image_data)
                    zip_file.writestr(f"slides/{filename}", image_bytes)
                except Exception as e:
                    logger.error(f"Error adding slide {slide.index}: {e}")

            # Add metadata
            metadata = self._generate_metadata(session)
            metadata_json = json.dumps(metadata, indent=2)
            zip_file.writestr("metadata.json", metadata_json)

            # Add text content file
            text_content = self._generate_text_file(session)
            zip_file.writestr("slide_texts.txt", text_content)

        zip_buffer.seek(0)
        return zip_buffer

    def _generate_text_file(self, session: SessionState) -> str:
        """Generate a text file with all slide content."""
        lines = [
            "Lucid Carousel Export",
            "=" * 50,
            f"Session: {session.session_id}",
            f"Slides: {len(session.slides)}",
            "",
            "Original Draft:",
            "-" * 20,
            session.draft_text or "(No draft)",
            "",
            "Slides:",
            "-" * 20,
        ]

        for slide in session.slides:
            lines.append(f"\nSlide {slide.index + 1}:")
            if slide.text.title:
                lines.append(f"  Title: {slide.text.title}")
            lines.append(f"  Body: {slide.text.body}")
            if slide.image_prompt:
                lines.append(f"  Image Prompt: {slide.image_prompt}")

        return "\n".join(lines)

    def export_single_slide(
        self,
        session_id: str,
        slide_index: int,
    ) -> Optional[BytesIO]:
        """Export a single slide as PNG."""
        session = session_manager.get_session(session_id)
        if not session or slide_index >= len(session.slides):
            return None

        slide = session.slides[slide_index]
        image_data = slide.final_image or slide.image_data
        if not image_data:
            return None

        try:
            image_bytes = base64.b64decode(image_data)
            buffer = BytesIO(image_bytes)
            buffer.seek(0)
            return buffer
        except Exception as e:
            logger.error(f"Error exporting slide {slide_index}: {e}")
            return None


# Global export service instance
export_service = ExportService()
