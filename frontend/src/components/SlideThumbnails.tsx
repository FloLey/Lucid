import { Slide } from '../types';

interface SlideThumbnailsProps {
  slides: Slide[];
  selectedSlide: number;
  onSlideChange: (index: number) => void;
}

export default function SlideThumbnails({
  slides,
  selectedSlide,
  onSlideChange,
}: SlideThumbnailsProps) {
  return (
    <div className="flex gap-2 overflow-x-auto pb-2">
      {slides.map((slide, index) => (
        <button
          key={index}
          onClick={() => onSlideChange(index)}
          className={`flex-shrink-0 w-16 rounded-lg overflow-hidden border-2 transition-colors ${
            index === selectedSlide
              ? 'border-lucid-600'
              : 'border-transparent hover:border-gray-300 dark:hover:border-gray-600'
          }`}
        >
          <div className="aspect-[4/5] bg-gray-100 dark:bg-gray-700">
            {slide.final_image_url || slide.background_image_url ? (
              <img
                src={slide.final_image_url || slide.background_image_url || ''}
                alt={`Slide ${index + 1}`}
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
