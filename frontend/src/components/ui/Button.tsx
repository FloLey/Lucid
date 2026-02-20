/**
 * Reusable Button primitive.
 *
 * Encapsulates the common Lucid button patterns to enforce visual consistency
 * and eliminate repeated Tailwind class strings across the app.
 */
import { ButtonHTMLAttributes } from 'react';

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';
type ButtonSize = 'sm' | 'md' | 'lg';

const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary:
    'bg-lucid-600 text-white hover:bg-lucid-700 disabled:opacity-50 disabled:cursor-not-allowed',
  secondary:
    'bg-gray-100 text-gray-700 hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed',
  ghost:
    'text-gray-600 hover:text-gray-800 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed',
  danger:
    'bg-red-600 text-white hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed',
};

const SIZE_CLASSES: Record<ButtonSize, string> = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-4 py-2 text-sm',
  lg: 'py-3 px-6 text-base',
};

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  fullWidth?: boolean;
}

export default function Button({
  variant = 'primary',
  size = 'md',
  fullWidth = false,
  className = '',
  children,
  ...rest
}: ButtonProps) {
  const base = 'font-medium rounded-lg transition-colors inline-flex items-center justify-center gap-2';
  const variantClass = VARIANT_CLASSES[variant];
  const sizeClass = SIZE_CLASSES[size];
  const widthClass = fullWidth ? 'w-full' : '';

  return (
    <button
      className={`${base} ${variantClass} ${sizeClass} ${widthClass} ${className}`.trim()}
      {...rest}
    >
      {children}
    </button>
  );
}
