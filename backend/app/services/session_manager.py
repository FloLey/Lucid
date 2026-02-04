"""Session management service."""

from typing import Dict, Optional
from datetime import datetime

from app.models.session import SessionState


class SessionManager:
    """Manages in-memory session state for all users."""

    def __init__(self):
        self._sessions: Dict[str, SessionState] = {}

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
        return session

    def get_session(self, session_id: str) -> Optional[SessionState]:
        """Get a session by ID."""
        return self._sessions.get(session_id)

    def update_session(self, session: SessionState) -> SessionState:
        """Update a session's state."""
        session.update_timestamp()
        self._sessions[session.session_id] = session
        return session

    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def advance_stage(self, session_id: str) -> Optional[SessionState]:
        """Advance session to next stage."""
        session = self.get_session(session_id)
        if not session:
            return None

        if session.current_stage < 4:
            session.current_stage += 1
            session.update_timestamp()

        return session

    def go_to_stage(self, session_id: str, stage: int) -> Optional[SessionState]:
        """Go to a specific stage."""
        session = self.get_session(session_id)
        if not session:
            return None

        if 1 <= stage <= 4:
            session.current_stage = stage
            session.update_timestamp()

        return session

    def clear_all(self):
        """Clear all sessions (for testing)."""
        self._sessions.clear()


# Global session manager instance
session_manager = SessionManager()
