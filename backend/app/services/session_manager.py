"""Session management service - placeholder for Step 2."""

from typing import Dict, Any


class SessionManager:
    """Manages in-memory session state."""

    def __init__(self):
        self.sessions: Dict[str, Any] = {}


# Global session manager instance
session_manager = SessionManager()
