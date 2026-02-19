import { createContext, useContext } from 'react';
import type { Project } from '../types';

export interface SessionContextValue {
  projectId: string;
  project: Project | null;
  loading: boolean;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  updateProject: (project: Project) => void;
  onNext: () => Promise<void>;
  onBack: () => Promise<void>;
}

export const SessionContext = createContext<SessionContextValue | null>(null);

export function useSessionContext(): SessionContextValue {
  const ctx = useContext(SessionContext);
  if (!ctx) {
    throw new Error('useSessionContext must be used within a SessionContext.Provider');
  }
  return ctx;
}
