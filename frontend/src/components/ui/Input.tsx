/**
 * Reusable Input and Textarea primitives.
 *
 * Encapsulates the common Lucid input patterns to enforce visual consistency
 * and eliminate repeated Tailwind class strings across the app.
 */
import { InputHTMLAttributes, TextareaHTMLAttributes } from 'react';

const BASE_INPUT_CLASSES =
  'border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-lucid-500 focus:border-transparent';

const FULL_WIDTH_CLASSES = 'w-full px-3 py-2';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  /** Extra Tailwind classes to merge in. */
  className?: string;
}

/** Single-line text input with Lucid focus ring. */
export function Input({ className = '', ...rest }: InputProps) {
  return (
    <input
      className={`${FULL_WIDTH_CLASSES} ${BASE_INPUT_CLASSES} ${className}`.trim()}
      {...rest}
    />
  );
}

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  className?: string;
}

/** Multi-line textarea with Lucid focus ring. */
export function Textarea({ className = '', ...rest }: TextareaProps) {
  return (
    <textarea
      className={`${FULL_WIDTH_CLASSES} ${BASE_INPUT_CLASSES} resize-none ${className}`.trim()}
      {...rest}
    />
  );
}
