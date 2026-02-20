"""Export service for generating ZIP archives of carousel slides."""

import json
import logging
import re
import zipfile
from datetime import datetime
from io import BytesIO
from typing import Optional

from app.models.project import ProjectState
from app.services.project_manager import ProjectManager
from app.services.image_service import ImageService

logger = logging.getLogger(__name__)


class ExportService:
    """Service for exporting carousel slides as ZIP archives."""

    def __init__(
        self,
        project_manager: Optional[ProjectManager] = None,
        image_service: Optional[ImageService] = None,
    ):
        self.project_manager = project_manager
        self.image_service = image_service
        if not self.project_manager:
            raise ValueError(
                "project_manager dependency must be provided to ExportService"
            )
        if not self.image_service:
            raise ValueError(
                "image_service dependency must be provided to ExportService"
            )

    def _sanitize_filename(self, text: str, max_length: int = 30) -> str:
        """Sanitize text for use in filename."""
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"\s+", "_", text)
        return text[:max_length].strip("_")

    def _generate_filename(self, index: int, title: Optional[str]) -> str:
        """Generate filename for a slide."""
        prefix = f"{index + 1:02d}"
        if title:
            sanitized = self._sanitize_filename(title)
            if sanitized:
                return f"{prefix}_{sanitized}.png"
        return f"{prefix}_slide.png"

    def _generate_metadata(self, project: ProjectState) -> dict:
        """Generate metadata for the export."""
        slides_meta = []
        for slide in project.slides:
            slides_meta.append(
                {
                    "index": slide.index,
                    "title": slide.text.title,
                    "body": slide.text.body,
                    "image_prompt": slide.image_prompt,
                    "style": slide.style.model_dump(),
                }
            )

        return {
            "project_id": project.project_id,
            "project_name": project.name,
            "created_at": project.created_at.isoformat(),
            "exported_at": datetime.utcnow().isoformat(),
            "num_slides": len(project.slides),
            "draft_text": project.draft_text,
            "image_style_instructions": project.image_style_instructions,
            "slides": slides_meta,
        }

    async def export_project(self, project_id: str) -> Optional[BytesIO]:
        """Export project slides as ZIP archive."""
        if not self.project_manager:
            return None
        project = await self.project_manager.get_project(project_id)
        if not project or not project.slides:
            return None

        zip_buffer = BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for slide in project.slides:
                image_data = slide.final_image or slide.image_data
                if not image_data:
                    continue

                filename = self._generate_filename(slide.index, slide.text.title)

                try:
                    image_bytes = self.image_service.read_image_bytes(image_data)
                    zip_file.writestr(f"slides/{filename}", image_bytes)
                except Exception as e:
                    logger.error(f"Error adding slide {slide.index}: {e}")

            metadata = self._generate_metadata(project)
            metadata_json = json.dumps(metadata, indent=2)
            zip_file.writestr("metadata.json", metadata_json)

            text_content = self._generate_text_file(project)
            zip_file.writestr("slide_texts.txt", text_content)

        zip_buffer.seek(0)
        return zip_buffer

    def _generate_text_file(self, project: ProjectState) -> str:
        """Generate a text file with all slide content."""
        lines = [
            "Lucid Carousel Export",
            "=" * 50,
            f"Project: {project.project_id} ({project.name})",
            f"Slides: {len(project.slides)}",
            "",
            "Original Draft:",
            "-" * 20,
            project.draft_text or "(No draft)",
            "",
            "Slides:",
            "-" * 20,
        ]

        for slide in project.slides:
            lines.append(f"\nSlide {slide.index + 1}:")
            if slide.text.title:
                lines.append(f"  Title: {slide.text.title}")
            lines.append(f"  Body: {slide.text.body}")
            if slide.image_prompt:
                lines.append(f"  Image Prompt: {slide.image_prompt}")

        return "\n".join(lines)

    async def export_single_slide(
        self,
        project_id: str,
        slide_index: int,
    ) -> Optional[BytesIO]:
        """Export a single slide as PNG."""
        if not self.project_manager:
            return None
        project = await self.project_manager.get_project(project_id)
        if not project or slide_index >= len(project.slides):
            return None

        slide = project.slides[slide_index]
        image_data = slide.final_image or slide.image_data
        if not image_data:
            return None

        try:
            image_bytes = self.image_service.read_image_bytes(image_data)
            buffer = BytesIO(image_bytes)
            buffer.seek(0)
            return buffer
        except Exception as e:
            logger.error(f"Error exporting slide {slide_index}: {e}")
            return None
