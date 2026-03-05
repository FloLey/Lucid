import { useState, useRef, useEffect, useCallback } from 'react';
import type { TextStyle, Corner } from '../types';

const MIN_BOX_WIDTH = 0.1;
const MIN_BOX_HEIGHT = 0.05;

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
  handleResizeMouseDown: (corner: Corner, e: React.MouseEvent) => void;
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
  const resizeStartRef = useRef<{ mouseX: number; mouseY: number; boxW: number; boxH: number; boxX: number; boxY: number; corner: Corner } | null>(null);

  const getContainerRect = useCallback(() => containerRef.current?.getBoundingClientRect(), [containerRef]);

  const handleBoxMouseDown = (box: SelectedBox, e: React.MouseEvent) => {
    const target = e.target as HTMLElement;
    if (target.getAttribute('contenteditable') === 'true') return;

    e.preventDefault();
    e.stopPropagation();
    setSelectedBox(box);
    const rect = getContainerRect();
    if (!rect || !style) return;

    const activeBox = box === 'title' ? style.title_box : style.body_box;
    dragStartRef.current = {
      mouseX: e.clientX,
      mouseY: e.clientY,
      boxX: activeBox.x_pct,
      boxY: activeBox.y_pct,
    };
    setDragging(true);
  };

  const handleResizeMouseDown = (corner: Corner, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const rect = getContainerRect();
    if (!rect || !style) return;

    const activeBox = selectedBox === 'title' ? style.title_box : style.body_box;
    resizeStartRef.current = {
      mouseX: e.clientX,
      mouseY: e.clientY,
      boxW: activeBox.w_pct,
      boxH: activeBox.h_pct,
      boxX: activeBox.x_pct,
      boxY: activeBox.y_pct,
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
        const start = resizeStartRef.current;
        const dx = (e.clientX - start.mouseX) / rect.width;
        const dy = (e.clientY - start.mouseY) / rect.height;

        let newX = start.boxX;
        let newY = start.boxY;
        let newW = start.boxW;
        let newH = start.boxH;

        if (start.corner.includes('r')) {
          newW = Math.max(MIN_BOX_WIDTH, Math.min(1 - start.boxX, start.boxW + dx));
        }
        if (start.corner.includes('l')) {
          const maxDx = start.boxW - MIN_BOX_WIDTH;
          const clampedDx = Math.max(-start.boxX, Math.min(maxDx, dx));
          newX = start.boxX + clampedDx;
          newW = start.boxW - clampedDx;
        }
        if (start.corner.includes('b')) {
          newH = Math.max(MIN_BOX_HEIGHT, Math.min(1 - start.boxY, start.boxH + dy));
        }
        if (start.corner.includes('t')) {
          const maxDy = start.boxH - MIN_BOX_HEIGHT;
          const clampedDy = Math.max(-start.boxY, Math.min(maxDy, dy));
          newY = start.boxY + clampedDy;
          newH = start.boxH - clampedDy;
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
