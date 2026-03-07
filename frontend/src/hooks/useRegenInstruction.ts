import { useState, useCallback } from 'react';

/**
 * Manages the paired state for a per-slide regeneration instruction UI:
 * which slide's regen input is open and what the user has typed.
 *
 * Usage:
 *   const { slide, instruction, setSlide, setInstruction, reset } = useRegenInstruction();
 */
export function useRegenInstruction() {
  const [slide, setSlide] = useState<number | null>(null);
  const [instruction, setInstruction] = useState('');

  /** Toggle the regen input for a given slide (opens it, or closes if already open). */
  const toggleSlide = useCallback((index: number) => {
    setSlide((prev) => (prev === index ? null : index));
    setInstruction('');
  }, []);

  /** Close the regen input and clear the instruction text. */
  const reset = useCallback(() => {
    setSlide(null);
    setInstruction('');
  }, []);

  return { slide, instruction, setSlide, setInstruction, toggleSlide, reset };
}
