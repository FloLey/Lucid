"""Session management service with JSON file persistence."""

import json
import os
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

from app.models.session import SessionState

# Path for session persistence (in project root for Docker volume mount)
SESSIONS_FILE = Path(__file__).parent.parent.parent / "sessions_db.json"


class SessionManager:
    """
    Manages session state with JSON file persistence.

    Persistence allows sessions to survive Docker hot-reloads during development,
    so developers can edit code and continue working on the same session.
    """

    def __init__(self):
        self._sessions: Dict[str, SessionState] = {}
        self._snapshots: Dict[str, SessionState] = {}
        self._load_from_file()

    def _load_from_file(self):
        """Load sessions from JSON file on startup."""
        if not SESSIONS_FILE.exists():
            return

        try:
            with open(SESSIONS_FILE, "r") as f:
                data = json.load(f)

            for session_id, session_data in data.items():
                try:
                    session = SessionState.model_validate(session_data)
                    self._sessions[session_id] = session
                except Exception as e:
                    # Skip invalid session data
                    print(f"Warning: Failed to load session {session_id}: {e}")

        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Failed to load sessions file: {e}")

    def _save_to_file(self):
        """Save all sessions to JSON file."""
        try:
            data = {}
            for session_id, session in self._sessions.items():
                # Use Pydantic's model_dump with mode='json' for serialization
                data[session_id] = session.model_dump(mode='json')

            with open(SESSIONS_FILE, "w") as f:
                json.dump(data, f, indent=2, default=str)

        except IOError as e:
            print(f"Warning: Failed to save sessions file: {e}")

    @property
    def sessions(self) -> Dict[str, SessionState]:
        """Get all sessions."""
        return self._sessions

    def create_session(self, session_id: str) -> SessionState:
        """Create a new session or return existing one."""
        if session_id in self._sessions:
            return self._sessions[session_id]

        session = SessionState(session_id=session_id)
        self._sessions[session_id] = session
        self._save_to_file()
        return session

    def get_session(self, session_id: str) -> Optional[SessionState]:
        """Get a session by ID."""
        return self._sessions.get(session_id)

    def update_session(self, session: SessionState) -> SessionState:
        """Update a session's state."""
        session.update_timestamp()
        self._sessions[session.session_id] = session
        self._save_to_file()
        return session

    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            self._save_to_file()
            return True
        return False

    def advance_stage(self, session_id: str) -> Optional[SessionState]:
        """Advance session to next stage."""
        session = self.get_session(session_id)
        if not session:
            return None

        if session.current_stage < 5:
            session.current_stage += 1
            session.update_timestamp()
            self._save_to_file()

        return session

    def previous_stage(self, session_id: str) -> Optional[SessionState]:
        """Go back to previous stage (bi-directional navigation)."""
        session = self.get_session(session_id)
        if not session:
            return None

        if session.current_stage > 1:
            session.current_stage -= 1
            session.update_timestamp()
            self._save_to_file()

        return session

    def go_to_stage(self, session_id: str, stage: int) -> Optional[SessionState]:
        """Go to a specific stage."""
        session = self.get_session(session_id)
        if not session:
            return None

        if 1 <= stage <= 5:
            session.current_stage = stage
            session.update_timestamp()
            self._save_to_file()

        return session

    def take_snapshot(self, session_id: str) -> None:
        """Deep copy current session state before agent writes."""
        session = self._sessions.get(session_id)
        if session:
            self._snapshots[session_id] = session.model_copy(deep=True)

    def restore_snapshot(self, session_id: str) -> Optional[SessionState]:
        """Restore session from snapshot and persist. Returns None if no snapshot."""
        snapshot = self._snapshots.pop(session_id, None)
        if snapshot:
            self._sessions[session_id] = snapshot
            self._save_to_file()
            return snapshot
        return None

    def get_snapshot(self, session_id: str) -> Optional[SessionState]:
        """Get the snapshot for a session (without removing it)."""
        return self._snapshots.get(session_id)

    def clear_all(self):
        """Clear all sessions (for testing)."""
        self._sessions.clear()
        self._snapshots.clear()
        # Also remove the file
        if SESSIONS_FILE.exists():
            try:
                SESSIONS_FILE.unlink()
            except IOError:
                pass


# Global session manager instance
session_manager = SessionManager()
