import { useState, useEffect, useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';
import type { Session } from '../types';
import * as api from '../services/api';

const SESSION_KEY = 'lucid_session_id';

export function useSession() {
  const [sessionId, setSessionId] = useState<string>('');
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
        setSession(sess);
      } catch (err) {
        console.error('Failed to create session:', err);
      }
    };

    initSession();
  }, []);

  const refreshSession = useCallback(async () => {
    if (!sessionId) return;
    try {
      const sess = await api.getSession(sessionId);
      setSession(sess);
    } catch (err) {
      console.error('Failed to refresh session:', err);
    }
  }, [sessionId]);

  const updateSession = useCallback((newSession: Session) => {
    setSession(newSession);
  }, []);

  const advanceStage = useCallback(async () => {
    if (!sessionId) return;
    setLoading(true);
    try {
      const sess = await api.advanceStage(sessionId);
      setSession(sess);
    } catch (err) {
      setError('Failed to advance stage');
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  const previousStage = useCallback(async () => {
    if (!sessionId) return;
    setLoading(true);
    try {
      const sess = await api.previousStage(sessionId);
      setSession(sess);
    } catch (err) {
      setError('Failed to go back');
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  const startNewSession = useCallback(async () => {
    const id = uuidv4();
    localStorage.setItem(SESSION_KEY, id);
    setSessionId(id);
    try {
      const sess = await api.createSession(id);
      setSession(sess);
    } catch (err) {
      setError('Failed to create new session');
    }
  }, []);

  return {
    sessionId,
    session,
    loading,
    error,
    setLoading,
    setError,
    updateSession,
    refreshSession,
    advanceStage,
    previousStage,
    startNewSession,
  };
}
