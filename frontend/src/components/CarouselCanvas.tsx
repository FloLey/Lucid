import { Slide, TextStyle } from '../types';
import Spinner from './Spinner';
import TextBoxOverlay from './TextBoxOverlay';

type SelectedBox = 'title' | 'body';

interface CarouselCanvasProps {
  containerRef: React.RefObject<HTMLDivElement>;
  currentSlide: Slide | undefined;
  selectedSlide: number;
  style: TextStyle | null;
  localTitle: string | null;
  localBody: string;
  selectedBox: SelectedBox;
  rendering: boolean;
  handleBoxMouseDown: (box: SelectedBox, e: React.MouseEvent) => void;
  handleResizeMouseDown: (corner: string, e: React.MouseEvent) => void;
  handleTextChange: (which: 'title' | 'body', text: string) => void;
}

export default function CarouselCanvas({
  containerRef,
  currentSlide,
  selectedSlide,
  style,
  localTitle,
  localBody,
  selectedBox,
  rendering,
  handleBoxMouseDown,
  handleResizeMouseDown,
  handleTextChange,
}: CarouselCanvasProps) {
  const hasTitle = !!localTitle;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
      <div
        ref={containerRef}
        className="relative aspect-[4/5] max-w-md mx-auto bg-gray-100 rounded-lg overflow-hidden select-none"
      >
        {/* Background image */}
        {currentSlide?.background_image_url && (
          <img
            src={currentSlide.background_image_url}
            alt={`Slide ${selectedSlide + 1} background`}
            className="absolute inset-0 w-full h-full object-cover"
            draggable={false}
          />
        )}

        {/* Title box overlay */}
        {hasTitle && style && (
          <TextBoxOverlay
            text={localTitle!}
            box={style.title_box}
            fontFamily={style.font_family}
            fontWeight={style.font_weight}
            fontSize={style.font_size_px}
            textColor={style.text_color}
            alignment={style.alignment as 'left' | 'center' | 'right'}
            stroke={style.stroke}
            isSelected={selectedBox === 'title'}
            onMouseDown={(e) => handleBoxMouseDown('title', e)}
            onResizeMouseDown={selectedBox === 'title' ? handleResizeMouseDown : undefined}
            onTextChange={(text) => handleTextChange('title', text)}
          />
        )}

        {/* Body box overlay */}
        {localBody && style && (
          <TextBoxOverlay
            text={localBody}
            box={style.body_box}
            fontFamily={style.font_family}
            fontWeight={Math.max(400, style.font_weight - 200)}
            fontSize={style.body_font_size_px}
            textColor={style.text_color}
            alignment={style.alignment as 'left' | 'center' | 'right'}
            stroke={style.stroke}
            isSelected={selectedBox === 'body'}
            onMouseDown={(e) => handleBoxMouseDown('body', e)}
            onResizeMouseDown={selectedBox === 'body' ? handleResizeMouseDown : undefined}
            onTextChange={(text) => handleTextChange('body', text)}
          />
        )}

        {/* No image placeholder */}
        {!currentSlide?.background_image_url && (
          <div className="absolute inset-0 flex items-center justify-center text-gray-400">
            No image
          </div>
        )}

        {/* Rendering indicator */}
        {rendering && (
          <div className="absolute top-2 right-2 flex items-center gap-1.5 bg-black/60 text-white text-xs px-2 py-1 rounded-full">
            <Spinner size="sm" />
            Rendering
          </div>
        )}
      </div>
    </div>
  );
}
