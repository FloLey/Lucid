import { useState, useEffect, useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';
import type { Session } from '../types';
import * as api from '../services/api';
import { getErrorMessage } from '../utils/error';

const SESSION_KEY = 'lucid_session_id';

/** Ensure array fields are never undefined. */
function normalizeSession(session: Session): Session {
  return {
    ...session,
    slides: session.slides ?? [],
    style_proposals: session.style_proposals ?? [],
  };
}

export function useSession() {
  const [sessionId, setSessionId] = useState<string>('');
  const [session, setSession] = useState<Session | null>(null);
  const [stageLoading, setStageLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const setNormalizedSession = useCallback((sess: Session) => {
    setSession(normalizeSession(sess));
  }, []);

  // Initialize session
  useEffect(() => {
    const initSession = async () => {
      let id = localStorage.getItem(SESSION_KEY);
      if (!id) {
        id = uuidv4();
        localStorage.setItem(SESSION_KEY, id);
      }
      setSessionId(id);

      try {
        const sess = await api.createSession(id);
        setNormalizedSession(sess);
      } catch (err) {
        console.error('Failed to create session:', err);
      }
    };

    initSession();
  }, [setNormalizedSession]);

  const refreshSession = useCallback(async () => {
    if (!sessionId) return;
    try {
      const sess = await api.getSession(sessionId);
      setNormalizedSession(sess);
    } catch (err) {
      console.error('Failed to refresh session:', err);
    }
  }, [sessionId, setNormalizedSession]);

  const updateSession = useCallback((newSession: Session) => {
    setNormalizedSession(newSession);
  }, [setNormalizedSession]);

  const advanceStage = useCallback(async () => {
    if (!sessionId) return;
    try {
      const sess = await api.advanceStage(sessionId);
      setNormalizedSession(sess);
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to advance stage'));
    }
  }, [sessionId, setNormalizedSession]);

  const previousStage = useCallback(async () => {
    if (!sessionId) return;
    try {
      const sess = await api.previousStage(sessionId);
      setNormalizedSession(sess);
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to go back'));
    }
  }, [sessionId, setNormalizedSession]);

  const goToStage = useCallback(async (stage: number) => {
    if (!sessionId) return;
    try {
      const sess = await api.goToStage(sessionId, stage);
      setNormalizedSession(sess);
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to navigate to stage'));
    }
  }, [sessionId, setNormalizedSession]);

  const startNewSession = useCallback(async () => {
    const id = uuidv4();
    localStorage.setItem(SESSION_KEY, id);
    setSessionId(id);
    try {
      const sess = await api.createSession(id);
      setNormalizedSession(sess);
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to create new session'));
    }
  }, [setNormalizedSession]);

  return {
    sessionId,
    session,
    stageLoading,
    error,
    setStageLoading,
    setError,
    updateSession,
    refreshSession,
    advanceStage,
    previousStage,
    goToStage,
    startNewSession,
  };
}
