import { useRef, useEffect, useState } from 'react';
import type { MatrixProject, MatrixCell } from '../../types';
import { getEffectiveDimensions } from '../../utils/matrix';
import MatrixAxisTitles from './MatrixAxisTitles';

const HEADER_W = 110; // width of row-label column (px)
const HEADER_H = 70;  // height of column-label row (px)
const CELL_SIZE = 140; // each matrix cell (px)
const LINE_HEIGHT = 16;
const MAX_TEXT_LINES = 3;

interface MatrixPosterViewProps {
  matrix: MatrixProject;
}

export default function MatrixPosterView({ matrix }: MatrixPosterViewProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isRendering, setIsRendering] = useState(true);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    setIsRendering(true);

    const { cells } = matrix;
    const { nRows, nCols } = getEffectiveDimensions(matrix);
    const W = HEADER_W + nCols * CELL_SIZE;
    const H = HEADER_H + nRows * CELL_SIZE;
    canvas.width = W;
    canvas.height = H;

    // Collect unique image URLs
    const imageCells = cells.filter((c) => c.image_url);
    const imageMap = new Map<string, HTMLImageElement>();

    const loadPromises = imageCells.map(
      (cell) =>
        new Promise<void>((resolve) => {
          const img = new Image();
          img.onload = () => {
            imageMap.set(`${cell.row}-${cell.col}`, img);
            resolve();
          };
          img.onerror = () => resolve();
          img.src = cell.image_url!;
        }),
    );

    Promise.all(loadPromises).then(() => {
      drawPoster(canvas, matrix, imageMap);
      setIsRendering(false);
    });
  }, [matrix]);

  const handleDownload = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const a = document.createElement('a');
    a.download = `matrix-${matrix.name.replace(/\s+/g, '-').toLowerCase()}.png`;
    a.href = canvas.toDataURL('image/png');
    a.click();
  };

  return (
    <div className="flex flex-col gap-3">
      {/* Toolbar */}
      <div className="flex items-center gap-2 shrink-0">
        {isRendering ? (
          <span className="text-xs text-gray-500 dark:text-gray-400">Rendering…</span>
        ) : (
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {matrix.input_mode === 'description' && matrix.n_rows > 0
              ? `${matrix.n_rows}×${matrix.n_cols}`
              : `${matrix.n}×${matrix.n}`} matrix poster
          </span>
        )}
        <button
          onClick={handleDownload}
          disabled={isRendering}
          className="ml-auto px-3 py-1.5 text-xs font-medium bg-lucid-600 text-white rounded-lg hover:bg-lucid-700 disabled:opacity-50 transition-colors"
        >
          Download PNG
        </button>
      </div>

      {/* Axis titles (description mode only) */}
      <MatrixAxisTitles matrix={matrix} paddingLeft={HEADER_W} />

      {/* Canvas */}
      <div className="overflow-auto border border-gray-200 dark:border-gray-700 rounded-xl">
        <canvas ref={canvasRef} className="block" style={{ maxWidth: '100%' }} />
      </div>
    </div>
  );
}

// ─── Drawing helpers ──────────────────────────────────────────────────────────

function getCell(cells: MatrixCell[], row: number, col: number): MatrixCell | undefined {
  return cells.find((c) => c.row === row && c.col === col);
}

function wrapText(
  ctx: CanvasRenderingContext2D,
  text: string,
  x: number,
  y: number,
  maxWidth: number,
  lineH: number,
  maxLines: number,
): void {
  const words = text.split(' ');
  const lines: string[] = [];
  let line = '';

  for (const word of words) {
    const testLine = line ? `${line} ${word}` : word;
    if (ctx.measureText(testLine).width > maxWidth && line) {
      lines.push(line);
      if (lines.length >= maxLines) break;
      line = word;
    } else {
      line = testLine;
    }
  }
  if (lines.length < maxLines && line) lines.push(line);

  const totalH = (lines.length - 1) * lineH;
  const startY = y - totalH / 2;
  lines.forEach((l, i) => {
    ctx.fillText(l, x, startY + i * lineH);
  });
}

function drawStrokedWrappedText(
  ctx: CanvasRenderingContext2D,
  text: string,
  x: number,
  y: number,
  maxWidth: number,
): void {
  const words = text.split(' ');
  const lines: string[] = [];
  let line = '';

  for (const word of words) {
    const testLine = line ? `${line} ${word}` : word;
    if (ctx.measureText(testLine).width > maxWidth && line) {
      lines.push(line);
      if (lines.length >= MAX_TEXT_LINES) break;
      line = word;
    } else {
      line = testLine;
    }
  }
  if (lines.length < MAX_TEXT_LINES && line) lines.push(line);

  const totalH = (lines.length - 1) * LINE_HEIGHT;
  const startY = y - totalH / 2;

  lines.forEach((l, i) => {
    const ly = startY + i * LINE_HEIGHT;
    ctx.strokeText(l, x, ly);
    ctx.fillText(l, x, ly);
  });
}

function drawPoster(
  canvas: HTMLCanvasElement,
  matrix: MatrixProject,
  imageMap: Map<string, HTMLImageElement>,
): void {
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  const { cells, input_mode } = matrix;
  const { nRows, nCols } = getEffectiveDimensions(matrix);

  // Helper to resolve header labels respecting description mode row/col labels
  const getRowLabel = (row: number): string => {
    if (input_mode === 'description' && matrix.row_labels?.length > row) {
      return matrix.row_labels[row];
    }
    const dc = getCell(cells, row, row);
    return dc?.row_descriptor || dc?.label || `R${row}`;
  };
  const getColLabel = (col: number): string => {
    if (input_mode === 'description' && matrix.col_labels?.length > col) {
      return matrix.col_labels[col];
    }
    const dc = getCell(cells, col, col);
    return dc?.col_descriptor || dc?.label || `C${col}`;
  };

  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';

  // ── Background ──────────────────────────────────────────────────────────────
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  // ── Column headers ──────────────────────────────────────────────────────────
  for (let col = 0; col < nCols; col++) {
    const label = getColLabel(col);
    const x = HEADER_W + col * CELL_SIZE;

    ctx.fillStyle = '#f1f5f9'; // slate-100
    ctx.fillRect(x, 0, CELL_SIZE, HEADER_H);

    ctx.font = 'bold 11px sans-serif';
    ctx.fillStyle = '#374151'; // gray-700
    wrapText(ctx, label, x + CELL_SIZE / 2, HEADER_H / 2, CELL_SIZE - 12, LINE_HEIGHT, 3);
  }

  // ── Row headers ─────────────────────────────────────────────────────────────
  for (let row = 0; row < nRows; row++) {
    const label = getRowLabel(row);
    const y = HEADER_H + row * CELL_SIZE;

    ctx.fillStyle = '#f1f5f9';
    ctx.fillRect(0, y, HEADER_W, CELL_SIZE);

    ctx.font = 'bold 11px sans-serif';
    ctx.fillStyle = '#374151';
    wrapText(ctx, label, HEADER_W / 2, y + CELL_SIZE / 2, HEADER_W - 12, LINE_HEIGHT, 3);
  }

  // ── Top-left corner ─────────────────────────────────────────────────────────
  ctx.fillStyle = '#e2e8f0'; // slate-200
  ctx.fillRect(0, 0, HEADER_W, HEADER_H);

  // ── Cells ────────────────────────────────────────────────────────────────────
  for (let row = 0; row < nRows; row++) {
    for (let col = 0; col < nCols; col++) {
      const cell = getCell(cells, row, col);
      const cx = HEADER_W + col * CELL_SIZE + CELL_SIZE / 2;
      const cy = HEADER_H + row * CELL_SIZE + CELL_SIZE / 2;
      const cellX = HEADER_W + col * CELL_SIZE;
      const cellY = HEADER_H + row * CELL_SIZE;
      const isDiagonal = row === col;

      if (isDiagonal && input_mode === 'theme') {
        // Theme mode diagonal: accent color
        ctx.fillStyle = '#dbeafe'; // blue-100
        ctx.fillRect(cellX, cellY, CELL_SIZE, CELL_SIZE);

        const label = cell?.label ?? '';
        if (label) {
          ctx.font = 'bold 13px sans-serif';
          ctx.fillStyle = '#1e40af'; // blue-800
          wrapText(ctx, label, cx, cy, CELL_SIZE - 12, LINE_HEIGHT, MAX_TEXT_LINES);
        }
      } else {
        // Off-diagonal or description-mode diagonal
        const img = imageMap.get(`${row}-${col}`);
        const concept = cell?.concept ?? '';

        if (img) {
          // Draw image background (cover)
          const scale = Math.max(CELL_SIZE / img.naturalWidth, CELL_SIZE / img.naturalHeight);
          const dw = img.naturalWidth * scale;
          const dh = img.naturalHeight * scale;
          const dx = cellX + (CELL_SIZE - dw) / 2;
          const dy = cellY + (CELL_SIZE - dh) / 2;

          ctx.save();
          ctx.beginPath();
          ctx.rect(cellX, cellY, CELL_SIZE, CELL_SIZE);
          ctx.clip();
          ctx.drawImage(img, dx, dy, dw, dh);
          // Slight dark overlay for text legibility
          ctx.fillStyle = 'rgba(0,0,0,0.25)';
          ctx.fillRect(cellX, cellY, CELL_SIZE, CELL_SIZE);
          ctx.restore();

          // White text with black stroke
          if (concept) {
            ctx.save();
            ctx.beginPath();
            ctx.rect(cellX, cellY, CELL_SIZE, CELL_SIZE);
            ctx.clip();
            ctx.font = 'bold 13px sans-serif';
            ctx.strokeStyle = 'black';
            ctx.lineWidth = 3;
            ctx.lineJoin = 'round';
            ctx.fillStyle = 'white';
            drawStrokedWrappedText(ctx, concept, cx, cy, CELL_SIZE - 12);
            ctx.restore();
          }
        } else {
          // White background, black text
          ctx.fillStyle = '#ffffff';
          ctx.fillRect(cellX, cellY, CELL_SIZE, CELL_SIZE);

          if (concept) {
            ctx.font = 'bold 13px sans-serif';
            ctx.fillStyle = '#111827'; // gray-900
            wrapText(ctx, concept, cx, cy, CELL_SIZE - 12, LINE_HEIGHT, MAX_TEXT_LINES);
          }
        }
      }
    }
  }

  // ── Grid lines ───────────────────────────────────────────────────────────────
  ctx.strokeStyle = '#e5e7eb'; // gray-200
  ctx.lineWidth = 1;

  // Vertical lines
  for (let col = 0; col <= nCols; col++) {
    const x = HEADER_W + col * CELL_SIZE;
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, canvas.height);
    ctx.stroke();
  }
  // Horizontal lines
  for (let row = 0; row <= nRows; row++) {
    const y = HEADER_H + row * CELL_SIZE;
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(canvas.width, y);
    ctx.stroke();
  }
  // Header separators (slightly darker)
  ctx.strokeStyle = '#9ca3af'; // gray-400
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(HEADER_W, 0);
  ctx.lineTo(HEADER_W, canvas.height);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(0, HEADER_H);
  ctx.lineTo(canvas.width, HEADER_H);
  ctx.stroke();
}
