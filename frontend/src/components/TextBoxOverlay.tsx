import { useRef, useEffect } from 'react';
import type { BoxStyle } from '../types';
import { IMAGE_SCALE_FACTOR } from '../constants';

interface TextBoxOverlayProps {
  text: string;
  box: BoxStyle;
  fontFamily: string;
  fontWeight: number;
  fontSize: number;
  textColor: string;
  alignment: 'left' | 'center' | 'right';
  stroke: { enabled: boolean; width_px: number; color: string };
  isSelected: boolean;
  onMouseDown: (e: React.MouseEvent) => void;
  onResizeMouseDown?: (corner: string, e: React.MouseEvent) => void;
  onTextChange: (text: string) => void;
}

export default function TextBoxOverlay({
  text,
  box,
  fontFamily,
  fontWeight,
  fontSize,
  textColor,
  alignment,
  stroke,
  isSelected,
  onMouseDown,
  onResizeMouseDown,
  onTextChange,
}: TextBoxOverlayProps) {
  const editRef = useRef<HTMLDivElement>(null);

  // Scale font size to preview — the canvas is ~400px wide, real image is 1080px
  const previewFontSize = Math.max(8, Math.round(fontSize * IMAGE_SCALE_FACTOR));

  const strokeStyle = stroke.enabled
    ? { WebkitTextStroke: `${stroke.width_px}px ${stroke.color}`, paintOrder: 'stroke fill' as const }
    : {};

  // Seed contentEditable text when it becomes selected OR when text changes (e.g., slide switch)
  const wasSelectedRef = useRef(false);
  const lastTextRef = useRef(text);
  useEffect(() => {
    if (editRef.current) {
      const becomingSelected = isSelected && !wasSelectedRef.current;
      const textChanged = text !== lastTextRef.current;

      if (becomingSelected || (isSelected && textChanged)) {
        editRef.current.innerText = text;
      }
    }
    wasSelectedRef.current = isSelected;
    lastTextRef.current = text;
  }, [isSelected, text]);

  const handleInput = () => {
    if (editRef.current) {
      onTextChange(editRef.current.innerText);
    }
  };

  return (
    <div
      className={`absolute cursor-move ${isSelected ? 'z-10' : 'z-0'}`}
      style={{
        left: `${box.x_pct * 100}%`,
        top: `${box.y_pct * 100}%`,
        width: `${box.w_pct * 100}%`,
        height: `${box.h_pct * 100}%`,
        outline: isSelected ? '2px solid #3b82f6' : '1px dashed rgba(156,163,175,0.5)',
        outlineOffset: '-1px',
        borderRadius: '4px',
        boxSizing: 'border-box',
      }}
      onMouseDown={onMouseDown}
    >
      <div
        className="w-full h-full overflow-hidden flex items-center"
        style={{
          padding: `${box.padding_pct * 100}%`,
          fontFamily,
          fontWeight,
          fontSize: `${previewFontSize}px`,
          lineHeight: 1.2,
          color: textColor,
          textAlign: alignment,
          wordBreak: 'break-word',
          ...strokeStyle,
        }}
      >
        {isSelected ? (
          <div
            ref={editRef}
            className="w-full cursor-text"
            contentEditable
            suppressContentEditableWarning
            onInput={handleInput}
            onMouseDown={(e) => e.stopPropagation()}
            style={{ outline: 'none', whiteSpace: 'pre-wrap' }}
          />
        ) : (
          <div className="w-full" style={{ whiteSpace: 'pre-wrap' }}>{text}</div>
        )}
      </div>

      {isSelected && onResizeMouseDown && (
        <>
          <ResizeHandle corner="tl" onMouseDown={onResizeMouseDown} />
          <ResizeHandle corner="tr" onMouseDown={onResizeMouseDown} />
          <ResizeHandle corner="bl" onMouseDown={onResizeMouseDown} />
          <ResizeHandle corner="br" onMouseDown={onResizeMouseDown} />
        </>
      )}
    </div>
  );
}

interface ResizeHandleProps {
  corner: string;
  onMouseDown: (corner: string, e: React.MouseEvent) => void;
}

function ResizeHandle({ corner, onMouseDown }: ResizeHandleProps) {
  const positionClasses: Record<string, string> = {
    tl: '-top-1 -left-1 cursor-nw-resize',
    tr: '-top-1 -right-1 cursor-ne-resize',
    bl: '-bottom-1 -left-1 cursor-sw-resize',
    br: '-bottom-1 -right-1 cursor-se-resize',
  };

  return (
    <div
      className={`absolute w-2.5 h-2.5 bg-white border-2 border-blue-500 rounded-full ${positionClasses[corner]}`}
      onMouseDown={(e) => onMouseDown(corner, e)}
    />
  );
}
