import { useState, useCallback, useRef } from 'react';
import { getErrorMessage } from '../utils/error';

interface UseApiActionOptions<TArgs extends any[], TResult> {
  action: (...args: TArgs) => Promise<TResult>;
  onSuccess?: (result: TResult) => void;
  onError?: (error: string) => void;
  successMessage?: string;
}

export function useApiAction<TArgs extends any[], TResult>({
  action,
  onSuccess,
  onError,
  successMessage
}: UseApiActionOptions<TArgs, TResult>) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TResult | null>(null);

  // Use refs for callbacks so execute stays stable
  const actionRef = useRef(action);
  const onSuccessRef = useRef(onSuccess);
  const onErrorRef = useRef(onError);
  actionRef.current = action;
  onSuccessRef.current = onSuccess;
  onErrorRef.current = onError;

  const execute = useCallback(async (...args: TArgs) => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await actionRef.current(...args);
      setResult(data);
      if (onSuccessRef.current) {
        onSuccessRef.current(data);
      }
      if (successMessage) {
        console.log(successMessage);
      }
      return data;
    } catch (err) {
      const message = getErrorMessage(err, 'Action failed');
      setError(message);
      if (onErrorRef.current) {
        onErrorRef.current(message);
      }
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [successMessage]);

  const reset = useCallback(() => {
    setError(null);
    setResult(null);
  }, []);

  return {
    execute,
    isLoading,
    error,
    result,
    reset
  };
}
