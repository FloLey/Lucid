import axios from 'axios';

export function getErrorMessage(err: unknown, fallback: string): string {
  if (axios.isAxiosError(err)) {
    const status = err.response?.status;
    const detail = err.response?.data?.detail;

    if (status === 503) {
      return 'AI service is temporarily unavailable. Please try again in a moment.';
    }

    if (detail) return `${fallback}: ${detail}`;
    return `${fallback}: ${status} ${err.response?.statusText || err.message}`;
  }
  if (err instanceof Error) return `${fallback}: ${err.message}`;
  return fallback;
}
