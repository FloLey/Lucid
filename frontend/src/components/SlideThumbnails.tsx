import { useRef, useState } from 'react';
import { Slide } from '../types';

interface SlideThumbnailsProps {
  slides: Slide[];
  selectedSlide: number;
  onSlideChange: (index: number) => void;
  onReorder?: (newOrder: number[]) => Promise<void>;
}

export default function SlideThumbnails({
  slides,
  selectedSlide,
  onSlideChange,
  onReorder,
}: SlideThumbnailsProps) {
  const dragIndexRef = useRef<number | null>(null);
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);

  const handleDragStart = (index: number) => {
    dragIndexRef.current = index;
  };

  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault();
    setDragOverIndex(index);
  };

  const handleDrop = async (e: React.DragEvent, dropIndex: number) => {
    e.preventDefault();
    const dragIndex = dragIndexRef.current;
    dragIndexRef.current = null;
    setDragOverIndex(null);
    if (dragIndex === null || dragIndex === dropIndex || !onReorder) return;

    // Build new order: remove drag source and insert at drop position
    const newOrder = slides.map((_, i) => i);
    newOrder.splice(dragIndex, 1);
    newOrder.splice(dropIndex, 0, dragIndex);
    try {
      await onReorder(newOrder);
    } catch {
      // Error handling is the caller's responsibility via the onReorder callback
    }
  };

  const handleDragEnd = () => {
    dragIndexRef.current = null;
    setDragOverIndex(null);
  };

  return (
    <div className="flex gap-2 overflow-x-auto pb-2">
      {slides.map((slide, index) => (
        <button
          key={slide.index}
          onClick={() => onSlideChange(index)}
          draggable={!!onReorder}
          onDragStart={() => handleDragStart(index)}
          onDragOver={(e) => handleDragOver(e, index)}
          onDrop={(e) => handleDrop(e, index)}
          onDragEnd={handleDragEnd}
          className={`flex-shrink-0 w-16 rounded-lg overflow-hidden border-2 transition-colors ${
            index === selectedSlide
              ? 'border-lucid-600'
              : dragOverIndex === index
                ? 'border-lucid-400 scale-105'
                : 'border-transparent hover:border-gray-300 dark:hover:border-gray-600'
          } ${onReorder ? 'cursor-grab active:cursor-grabbing' : ''}`}
        >
          <div className="aspect-[4/5] bg-gray-100 dark:bg-gray-700">
            {slide.final_image_url || slide.background_image_url ? (
              <img
                src={slide.final_image_url || slide.background_image_url || ''}
                alt={`Slide ${index + 1}`}
                loading="lazy"
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-xs text-gray-400">
                {index + 1}
              </div>
            )}
          </div>
        </button>
      ))}
    </div>
  );
}
