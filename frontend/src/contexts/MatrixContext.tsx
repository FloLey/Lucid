import {
  useState,
  useEffect,
  useCallback,
  useMemo,
  createContext,
  useContext,
} from 'react';
import type { ReactNode } from 'react';
import type { MatrixProject, MatrixProjectCard } from '../types';
import * as api from '../services/api';
import { getErrorMessage } from '../utils/error';

interface MatrixContextValue {
  matrices: MatrixProjectCard[];
  matricesLoading: boolean;
  currentMatrix: MatrixProject | null;
  error: string | null;
  setError: (error: string | null) => void;
  updateMatrix: (matrix: MatrixProject) => void;
  openMatrix: (id: string) => Promise<void>;
  closeMatrix: () => void;
  createMatrix: (params: api.CreateMatrixParams) => Promise<MatrixProject>;
  deleteMatrix: (id: string) => Promise<void>;
  refreshMatrices: () => Promise<void>;
}

const MatrixContext = createContext<MatrixContextValue | null>(null);

export function MatrixProvider({ children }: { children: ReactNode }) {
  const [matrices, setMatrices] = useState<MatrixProjectCard[]>([]);
  const [currentMatrix, setCurrentMatrix] = useState<MatrixProject | null>(null);
  const [matricesLoading, setMatricesLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refreshMatrices = useCallback(async () => {
    try {
      const cards = await api.listMatrices();
      setMatrices(cards);
    } catch (err) {
      console.error('Failed to refresh matrices:', err);
    }
  }, []);

  useEffect(() => {
    refreshMatrices().finally(() => setMatricesLoading(false));
  }, [refreshMatrices]);

  const openMatrix = useCallback(
    async (id: string) => {
      try {
        const m = await api.getMatrix(id);
        setCurrentMatrix(m);
        setError(null);
      } catch (err) {
        setError(getErrorMessage(err, 'Failed to open matrix'));
      }
    },
    [],
  );

  const closeMatrix = useCallback(() => {
    setCurrentMatrix(null);
    refreshMatrices();
  }, [refreshMatrices]);

  const createMatrix = useCallback(
    async (params: api.CreateMatrixParams): Promise<MatrixProject> => {
      const m = await api.createMatrix(params);
      setCurrentMatrix(m);
      await refreshMatrices();
      return m;
    },
    [refreshMatrices],
  );

  const deleteMatrix = useCallback(
    async (id: string) => {
      try {
        await api.deleteMatrix(id);
        if (currentMatrix?.id === id) setCurrentMatrix(null);
        await refreshMatrices();
      } catch (err) {
        setError(getErrorMessage(err, 'Failed to delete matrix'));
      }
    },
    [currentMatrix, refreshMatrices],
  );

  const updateMatrix = useCallback((m: MatrixProject) => {
    setCurrentMatrix(m);
  }, []);

  const value = useMemo<MatrixContextValue>(
    () => ({
      matrices,
      matricesLoading,
      currentMatrix,
      error,
      setError,
      updateMatrix,
      openMatrix,
      closeMatrix,
      createMatrix,
      deleteMatrix,
      refreshMatrices,
    }),
    [
      matrices,
      matricesLoading,
      currentMatrix,
      error,
      updateMatrix,
      openMatrix,
      closeMatrix,
      createMatrix,
      deleteMatrix,
      refreshMatrices,
    ],
  );

  return <MatrixContext.Provider value={value}>{children}</MatrixContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useMatrix(): MatrixContextValue {
  const ctx = useContext(MatrixContext);
  if (!ctx) throw new Error('useMatrix must be used within a MatrixProvider');
  return ctx;
}
