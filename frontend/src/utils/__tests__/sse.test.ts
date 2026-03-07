import { describe, it, expect, vi } from 'vitest';
import { parseSSELine, SSE_DATA_PREFIX } from '../sse';

describe('SSE_DATA_PREFIX', () => {
  it('is "data: "', () => {
    expect(SSE_DATA_PREFIX).toBe('data: ');
  });
});

describe('parseSSELine', () => {
  it('returns parsed object for a valid data line', () => {
    const result = parseSSELine<{ text: string }>('data: {"text":"hello"}');
    expect(result).toEqual({ text: 'hello' });
  });

  it('returns null for a line not starting with "data: "', () => {
    expect(parseSSELine('event: ping')).toBeNull();
    expect(parseSSELine('')).toBeNull();
    expect(parseSSELine(': heartbeat')).toBeNull();
  });

  it('returns null and warns on invalid JSON', () => {
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const result = parseSSELine('data: not-valid-json{');
    expect(result).toBeNull();
    expect(warnSpy).toHaveBeenCalled();
    warnSpy.mockRestore();
  });

  it('handles nested objects', () => {
    const payload = { type: 'cell', row: 1, col: 2, concept: 'test' };
    const line = `data: ${JSON.stringify(payload)}`;
    expect(parseSSELine(line)).toEqual(payload);
  });

  it('handles boolean and number payloads', () => {
    expect(parseSSELine('data: true')).toBe(true);
    expect(parseSSELine('data: 42')).toBe(42);
  });
});
