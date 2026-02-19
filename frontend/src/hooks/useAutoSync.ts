import { useState, useRef, useCallback, useEffect } from 'react';

interface UseAutoSyncOptions<T> {
  initialValue: T;
  syncDelay?: number;
  onSync: (value: T) => Promise<void>;
  shouldSync?: (prev: T, next: T) => boolean;
}

export function useAutoSync<T>({
  initialValue,
  syncDelay = 1000,
  onSync,
  shouldSync = (prev, next) => prev !== next
}: UseAutoSyncOptions<T>) {
  const [value, setValue] = useState<T>(initialValue);
  const [isDirty, setIsDirty] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const syncTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const previousValueRef = useRef<T>(initialValue);

  const scheduleSync = useCallback(() => {
    if (syncTimerRef.current) {
      clearTimeout(syncTimerRef.current);
    }

    syncTimerRef.current = setTimeout(async () => {
      if (!isDirty) return;

      setIsSyncing(true);
      try {
        await onSync(value);
        setIsDirty(false);
        previousValueRef.current = value;
      } catch (error) {
        console.error('Sync failed:', error);
        // Optionally retry or show error
      } finally {
        setIsSyncing(false);
      }
    }, syncDelay);
  }, [value, isDirty, syncDelay, onSync]);

  const updateValue = useCallback((newValue: T) => {
    if (shouldSync(previousValueRef.current, newValue)) {
      setValue(newValue);
      setIsDirty(true);
    }
  }, [shouldSync]);

  // Schedule sync when dirty
  useEffect(() => {
    if (isDirty) {
      scheduleSync();
    }
    return () => {
      if (syncTimerRef.current) {
        clearTimeout(syncTimerRef.current);
      }
    };
  }, [isDirty, scheduleSync]);

  // Reset when initial value changes externally
  useEffect(() => {
    if (!isDirty && value !== initialValue) {
      setValue(initialValue);
      previousValueRef.current = initialValue;
    }
  }, [initialValue, isDirty, value]);

  return {
    value,
    setValue: updateValue,
    isDirty,
    isSyncing,
    forceSync: async () => {
      if (syncTimerRef.current) {
        clearTimeout(syncTimerRef.current);
      }
      setIsSyncing(true);
      try {
        await onSync(value);
        setIsDirty(false);
        previousValueRef.current = value;
      } finally {
        setIsSyncing(false);
      }
    }
  };
}