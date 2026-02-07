import axios from 'axios';

export function getErrorMessage(err: unknown, fallback: string): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail;
    const status = err.response?.status;
    if (detail) return `${fallback}: ${detail} (${status})`;
    return `${fallback}: ${status} ${err.response?.statusText || err.message}`;
  }
  if (err instanceof Error) return `${fallback}: ${err.message}`;
  return fallback;
}
