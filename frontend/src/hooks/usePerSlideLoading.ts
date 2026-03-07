import { useState, useCallback } from 'react';

/**
 * Tracks which slide indices currently have an in-flight async operation.
 *
 * Usage:
 *   const { isLoading, startLoading, stopLoading } = usePerSlideLoading();
 */
export function usePerSlideLoading() {
  const [loadingSlides, setLoadingSlides] = useState<Set<number>>(new Set());

  const isLoading = useCallback(
    (index: number) => loadingSlides.has(index),
    [loadingSlides],
  );

  const startLoading = useCallback((index: number) => {
    setLoadingSlides((prev) => new Set(prev).add(index));
  }, []);

  const stopLoading = useCallback((index: number) => {
    setLoadingSlides((prev) => {
      const next = new Set(prev);
      next.delete(index);
      return next;
    });
  }, []);

  return { isLoading, startLoading, stopLoading, loadingSlides };
}
