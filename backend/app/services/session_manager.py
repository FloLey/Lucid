"""Session management service with per-session JSON file persistence."""

import asyncio
import logging
import threading
from typing import Dict, Optional
from contextlib import asynccontextmanager

from app.models.session import SessionState
from app.services.session_store import FileSessionStore

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages session state with in-memory cache and file persistence.

    All mutation methods are async-only. Delegates file I/O to FileSessionStore.
    """

    def __init__(self, store: Optional[FileSessionStore] = None):
        """
        Initialize the SessionManager.

        Args:
            store: The persistence backend. Defaults to a new FileSessionStore.
        """
        self._store = store or FileSessionStore()
        self._sessions: Dict[str, SessionState] = {}
        self._global_lock = threading.Lock()
        self._session_locks: Dict[str, threading.Lock] = {}
        self._sessions = self._store.load_all()

    def _get_session_lock(self, session_id: str) -> threading.Lock:
        """Get or create a lock for a specific session."""
        with self._global_lock:
            if session_id not in self._session_locks:
                self._session_locks[session_id] = threading.Lock()
            return self._session_locks[session_id]

    @asynccontextmanager
    async def _async_lock(self):
        """Async context manager for acquiring the global threading lock."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._global_lock.acquire)
        try:
            yield
        finally:
            self._global_lock.release()

    @property
    def sessions(self) -> Dict[str, SessionState]:
        """Get all sessions."""
        return self._sessions

    async def create_session(self, session_id: str) -> SessionState:
        """Create a new session or return existing one."""
        async with self._async_lock():
            if session_id in self._sessions:
                return self._sessions[session_id]

            session = SessionState(session_id=session_id)
            self._sessions[session_id] = session
            await self._store.save(session)
            return session

    async def get_session(self, session_id: str) -> Optional[SessionState]:
        """Get a session by ID."""
        async with self._async_lock():
            return self._sessions.get(session_id)

    async def update_session(self, session: SessionState) -> SessionState:
        """Update a session's state."""
        session.update_timestamp()
        async with self._async_lock():
            self._sessions[session.session_id] = session
            await self._store.save(session)
            return session

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        async with self._async_lock():
            if session_id in self._sessions:
                del self._sessions[session_id]
                self._store.delete(session_id)
                return True
            return False

    async def advance_stage(self, session_id: str) -> Optional[SessionState]:
        """Advance session to next stage."""
        async with self._async_lock():
            session = self._sessions.get(session_id)
            if not session:
                return None

            if session.current_stage < 5:
                session.current_stage += 1
                session.update_timestamp()
                await self._store.save(session)

            return session

    async def previous_stage(self, session_id: str) -> Optional[SessionState]:
        """Go back to previous stage."""
        async with self._async_lock():
            session = self._sessions.get(session_id)
            if not session:
                return None

            if session.current_stage > 1:
                session.current_stage -= 1
                session.update_timestamp()
                await self._store.save(session)

            return session

    async def go_to_stage(
        self, session_id: str, stage: int
    ) -> Optional[SessionState]:
        """Go to a specific stage."""
        async with self._async_lock():
            session = self._sessions.get(session_id)
            if not session:
                return None

            if 1 <= stage <= 5:
                session.current_stage = stage
                session.update_timestamp()
                await self._store.save(session)

            return session

    def clear_all(self):
        """Wipe all sessions from memory and disk. Primarily used for testing."""
        with self._global_lock:
            self._sessions.clear()
            self._store.clear_all()

    @asynccontextmanager
    async def session_context(self, session_id: str):
        """Async context manager for safe session access with per-session lock."""
        lock = self._get_session_lock(session_id)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lock.acquire)
        try:
            yield self._sessions.get(session_id)
        finally:
            lock.release()


# Module-level singleton — used by test files and the DI container
session_manager = SessionManager()
