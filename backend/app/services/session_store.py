"""File-based session persistence store."""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Dict

import aiofiles  # type: ignore

from app.models.session import SessionState

logger = logging.getLogger(__name__)

# Directory for per-session persistence files
DATA_DIR = Path(__file__).parent.parent.parent / "data"


class FileSessionStore:
    """Handles file I/O for session persistence.

    Each session is stored as a separate file (sess_{id}.json) using atomic
    writes (write to .tmp then os.replace) to prevent corruption.
    """

    def __init__(self, data_dir: Path = DATA_DIR):
        """Initialize the store and ensure the data directory exists."""
        self._data_dir = data_dir
        self._data_dir.mkdir(exist_ok=True)

    def _get_path(self, session_id: str) -> Path:
        """
        Calculate the JSON file path for a given session identifier.

        Args:
            session_id: The unique session string.
        """
        return self._data_dir / f"sess_{session_id}.json"

    def load_all(self) -> Dict[str, SessionState]:
        """Load all sessions from individual JSON files (sync, used at startup)."""
        sessions: Dict[str, SessionState] = {}
        for path in self._data_dir.glob("sess_*.json"):
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                session = SessionState.model_validate(data)
                sessions[session.session_id] = session
            except Exception as e:
                logger.warning(f"Failed to load session from {path.name}: {e}")
        return sessions

    async def save(self, session: SessionState) -> None:
        """Save a single session using atomic write with retry."""
        path = self._get_path(session.session_id)
        tmp_path = path.with_suffix(".tmp")
        max_retries = 3
        retry_delay = 0.1

        for attempt in range(max_retries):
            try:
                data = session.model_dump(mode="json")
                async with aiofiles.open(tmp_path, "w") as f:
                    await f.write(json.dumps(data, indent=2, default=str))
                os.replace(tmp_path, path)
                return
            except (IOError, OSError) as e:
                if attempt == max_retries - 1:
                    logger.error(
                        f"Failed to save session {session.session_id} "
                        f"after {max_retries} attempts: {e}"
                    )
                    raise
                await asyncio.sleep(retry_delay * (2**attempt))

    def delete(self, session_id: str) -> None:
        """Delete a session's file from disk."""
        path = self._get_path(session_id)
        try:
            if path.exists():
                path.unlink()
        except IOError as e:
            logger.warning(f"Failed to delete session file for {session_id}: {e}")

    def clear_all(self) -> None:
        """Remove all session files from disk."""
        for path in self._data_dir.glob("sess_*.json"):
            try:
                path.unlink()
            except IOError:
                pass
