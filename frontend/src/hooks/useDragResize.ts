import { useState, useRef, useEffect, useCallback } from 'react';
import type { TextStyle } from '../types';

type SelectedBox = 'title' | 'body';

interface UseDragResizeOptions {
  containerRef: React.RefObject<HTMLDivElement | null>;
  style: TextStyle | null;
  selectedBox: SelectedBox;
  setSelectedBox: (box: SelectedBox) => void;
  updateLocalStyle: (updates: Record<string, unknown>) => void;
}

interface UseDragResizeResult {
  dragging: boolean;
  resizing: boolean;
  handleBoxMouseDown: (box: SelectedBox, e: React.MouseEvent) => void;
  handleResizeMouseDown: (corner: string, e: React.MouseEvent) => void;
}

export function useDragResize({
  containerRef,
  style,
  selectedBox,
  setSelectedBox,
  updateLocalStyle,
}: UseDragResizeOptions): UseDragResizeResult {
  const [dragging, setDragging] = useState(false);
  const [resizing, setResizing] = useState(false);
  const dragStartRef = useRef<{ mouseX: number; mouseY: number; boxX: number; boxY: number } | null>(null);
  const resizeStartRef = useRef<{ mouseX: number; mouseY: number; boxW: number; boxH: number; boxX: number; boxY: number; corner: string } | null>(null);

  const getContainerRect = useCallback(() => containerRef.current?.getBoundingClientRect(), [containerRef]);

  const handleBoxMouseDown = (box: SelectedBox, e: React.MouseEvent) => {
    const target = e.target as HTMLElement;
    if (target.getAttribute('contenteditable') === 'true') return;

    e.preventDefault();
    e.stopPropagation();
    setSelectedBox(box);
    const rect = getContainerRect();
    if (!rect || !style) return;

    const bx = box === 'title' ? style.title_box : style.body_box;
    dragStartRef.current = {
      mouseX: e.clientX,
      mouseY: e.clientY,
      boxX: bx.x_pct,
      boxY: bx.y_pct,
    };
    setDragging(true);
  };

  const handleResizeMouseDown = (corner: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const rect = getContainerRect();
    if (!rect || !style) return;

    const bx = selectedBox === 'title' ? style.title_box : style.body_box;
    resizeStartRef.current = {
      mouseX: e.clientX,
      mouseY: e.clientY,
      boxW: bx.w_pct,
      boxH: bx.h_pct,
      boxX: bx.x_pct,
      boxY: bx.y_pct,
      corner,
    };
    setResizing(true);
  };

  useEffect(() => {
    if (!dragging && !resizing) return;

    const handleMouseMove = (e: MouseEvent) => {
      const rect = getContainerRect();
      if (!rect) return;

      if (dragging && dragStartRef.current) {
        const dx = (e.clientX - dragStartRef.current.mouseX) / rect.width;
        const dy = (e.clientY - dragStartRef.current.mouseY) / rect.height;
        const newX = Math.max(0, Math.min(1, dragStartRef.current.boxX + dx));
        const newY = Math.max(0, Math.min(1, dragStartRef.current.boxY + dy));
        const key = selectedBox === 'title' ? 'title_box' : 'body_box';
        updateLocalStyle({ [key]: { x_pct: newX, y_pct: newY } });
      }

      if (resizing && resizeStartRef.current) {
        const s = resizeStartRef.current;
        const dx = (e.clientX - s.mouseX) / rect.width;
        const dy = (e.clientY - s.mouseY) / rect.height;

        let newX = s.boxX;
        let newY = s.boxY;
        let newW = s.boxW;
        let newH = s.boxH;

        if (s.corner.includes('r')) {
          newW = Math.max(0.1, Math.min(1 - s.boxX, s.boxW + dx));
        }
        if (s.corner.includes('l')) {
          const maxDx = s.boxW - 0.1;
          const clampedDx = Math.max(-s.boxX, Math.min(maxDx, dx));
          newX = s.boxX + clampedDx;
          newW = s.boxW - clampedDx;
        }
        if (s.corner.includes('b')) {
          newH = Math.max(0.05, Math.min(1 - s.boxY, s.boxH + dy));
        }
        if (s.corner.includes('t')) {
          const maxDy = s.boxH - 0.05;
          const clampedDy = Math.max(-s.boxY, Math.min(maxDy, dy));
          newY = s.boxY + clampedDy;
          newH = s.boxH - clampedDy;
        }

        const key = selectedBox === 'title' ? 'title_box' : 'body_box';
        updateLocalStyle({ [key]: { x_pct: newX, y_pct: newY, w_pct: newW, h_pct: newH } });
      }
    };

    const handleMouseUp = () => {
      setDragging(false);
      setResizing(false);
      dragStartRef.current = null;
      resizeStartRef.current = null;
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [dragging, resizing, selectedBox, updateLocalStyle, getContainerRect]);

  return { dragging, resizing, handleBoxMouseDown, handleResizeMouseDown };
}
