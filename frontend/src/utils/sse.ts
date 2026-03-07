/**
 * Shared utilities for parsing Server-Sent Events (SSE) streams.
 *
 * Both {@link useStreamingText} and {@link useMatrixStream} consume SSE
 * responses from the backend.  This module centralises the line-prefix
 * constant and the per-line parse helper so the two hooks stay in sync.
 */

/** Standard SSE line prefix for data events. */
export const SSE_DATA_PREFIX = 'data: ';

/**
 * Parse a single SSE data line into a typed value.
 *
 * Returns `null` (and logs a warning) if:
 * - the line does not start with {@link SSE_DATA_PREFIX}, or
 * - `JSON.parse` throws.
 *
 * @param line - A raw text line from the SSE stream (not trimmed).
 * @returns The parsed object cast to `T`, or `null` on failure.
 */
export function parseSSELine<T>(line: string): T | null {
  if (!line.startsWith(SSE_DATA_PREFIX)) return null;
  try {
    return JSON.parse(line.slice(SSE_DATA_PREFIX.length)) as T;
  } catch (e) {
    console.warn('Failed to parse SSE message:', line, e);
    return null;
  }
}
