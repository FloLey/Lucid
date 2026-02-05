import { useState, useEffect } from 'react';
import type { Session, TextStyle } from '../types';
import * as api from '../services/api';

interface Stage4Props {
  sessionId: string;
  session: Session | null;
  loading: boolean;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  updateSession: (session: Session) => void;
  onNext: () => void;
}

export default function Stage4({
  sessionId,
  session,
  loading,
  setLoading,
  setError,
  updateSession,
}: Stage4Props) {
  const [selectedSlide, setSelectedSlide] = useState(0);
  const [presets, setPresets] = useState<Record<string, unknown>>({});

  useEffect(() => {
    api.getPresets().then(setPresets).catch(console.error);
  }, []);

  const handleApplyAll = async () => {
    setLoading(true);
    setError(null);
    try {
      const sess = await api.applyTextToAll(sessionId);
      updateSession(sess);
    } catch (err) {
      setError('Failed to apply typography');
    } finally {
      setLoading(false);
    }
  };

  const handleApplySlide = async (index: number) => {
    setLoading(true);
    try {
      const sess = await api.applyTextToSlide(sessionId, index);
      updateSession(sess);
    } catch (err) {
      setError('Failed to apply typography to slide');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateStyle = async (style: Partial<TextStyle>) => {
    try {
      const sess = await api.updateStyle(sessionId, selectedSlide, style as Record<string, unknown>);
      updateSession(sess);
    } catch (err) {
      setError('Failed to update style');
    }
  };

  const handleExport = () => {
    window.open(api.getExportZipUrl(sessionId), '_blank');
  };

  const slides = session?.slides || [];
  const currentSlide = slides[selectedSlide];
  const hasFinalImages = slides.some((s) => s.final_image);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Typography & Layout</h2>
          <p className="text-sm text-gray-500">
            Apply text styling to your carousel slides
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={handleApplyAll}
            disabled={loading}
            className="px-4 py-2 bg-white border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
          >
            {loading ? 'Applying...' : 'Apply to All'}
          </button>
          {hasFinalImages && (
            <button
              onClick={handleExport}
              className="px-4 py-2 bg-lucid-600 text-white font-medium rounded-lg hover:bg-lucid-700 transition-colors"
            >
              Export ZIP
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Preview */}
        <div className="lg:col-span-2 space-y-4">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
            <div className="aspect-[4/5] max-w-md mx-auto bg-gray-100 rounded-lg overflow-hidden">
              {currentSlide?.final_image ? (
                <img
                  src={`data:image/png;base64,${currentSlide.final_image}`}
                  alt={`Slide ${selectedSlide + 1}`}
                  className="w-full h-full object-cover"
                />
              ) : currentSlide?.image_data ? (
                <img
                  src={`data:image/png;base64,${currentSlide.image_data}`}
                  alt={`Slide ${selectedSlide + 1} (no text)`}
                  className="w-full h-full object-cover opacity-50"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-gray-400">
                  No image
                </div>
              )}
            </div>
          </div>

          {/* Slide Selector */}
          <div className="flex gap-2 overflow-x-auto pb-2">
            {slides.map((slide, index) => (
              <button
                key={index}
                onClick={() => setSelectedSlide(index)}
                className={`flex-shrink-0 w-16 rounded-lg overflow-hidden border-2 transition-colors ${
                  index === selectedSlide
                    ? 'border-lucid-600'
                    : 'border-transparent hover:border-gray-300'
                }`}
              >
                <div className="aspect-[4/5] bg-gray-100">
                  {slide.final_image || slide.image_data ? (
                    <img
                      src={`data:image/png;base64,${slide.final_image || slide.image_data}`}
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
        </div>

        {/* Style Controls */}
        <div className="space-y-4">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
            <h3 className="font-semibold text-gray-900 mb-4">Style Controls</h3>

            {currentSlide && (
              <StyleControls
                style={currentSlide.style}
                presets={presets}
                onUpdate={handleUpdateStyle}
                onApply={() => handleApplySlide(selectedSlide)}
                loading={loading}
              />
            )}
          </div>

          {/* Slide Text */}
          {currentSlide && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
              <h3 className="font-semibold text-gray-900 mb-2">Slide Text</h3>
              {currentSlide.text.title && (
                <p className="text-sm font-medium text-gray-900">{currentSlide.text.title}</p>
              )}
              <p className="text-sm text-gray-700">{currentSlide.text.body}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

interface StyleControlsProps {
  style: TextStyle;
  presets: Record<string, unknown>;
  onUpdate: (style: Partial<TextStyle>) => void;
  onApply: () => void;
  loading: boolean;
}

function StyleControls({ style, presets, onUpdate, onApply, loading }: StyleControlsProps) {
  return (
    <div className="space-y-4">
      {/* Presets */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">Presets</label>
        <div className="flex flex-wrap gap-2">
          {Object.keys(presets).map((name) => (
            <button
              key={name}
              onClick={() => onUpdate(presets[name] as Partial<TextStyle>)}
              className="px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded-full capitalize transition-colors"
            >
              {name}
            </button>
          ))}
        </div>
      </div>

      {/* Font Size */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Font Size: {style.font_size_px}px
        </label>
        <input
          type="range"
          min="24"
          max="120"
          value={style.font_size_px}
          onChange={(e) => onUpdate({ font_size_px: Number(e.target.value) })}
          className="w-full"
        />
      </div>

      {/* Text Color */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Text Color</label>
        <input
          type="color"
          value={style.text_color}
          onChange={(e) => onUpdate({ text_color: e.target.value })}
          className="w-full h-8 rounded cursor-pointer"
        />
      </div>

      {/* Alignment */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Alignment</label>
        <div className="flex gap-2">
          {(['left', 'center', 'right'] as const).map((align) => (
            <button
              key={align}
              onClick={() => onUpdate({ alignment: align })}
              className={`flex-1 py-1.5 text-xs rounded capitalize ${
                style.alignment === align
                  ? 'bg-lucid-600 text-white'
                  : 'bg-gray-100 hover:bg-gray-200'
              }`}
            >
              {align}
            </button>
          ))}
        </div>
      </div>

      {/* Position X */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          X Position: {Math.round(style.box.x_pct * 100)}%
        </label>
        <input
          type="range"
          min="0"
          max="50"
          value={style.box.x_pct * 100}
          onChange={(e) => onUpdate({ box: { ...style.box, x_pct: Number(e.target.value) / 100 } })}
          className="w-full"
        />
      </div>

      {/* Position Y */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Y Position: {Math.round(style.box.y_pct * 100)}%
        </label>
        <input
          type="range"
          min="0"
          max="70"
          value={style.box.y_pct * 100}
          onChange={(e) => onUpdate({ box: { ...style.box, y_pct: Number(e.target.value) / 100 } })}
          className="w-full"
        />
      </div>

      {/* Stroke Toggle */}
      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          checked={style.stroke.enabled}
          onChange={(e) => onUpdate({ stroke: { ...style.stroke, enabled: e.target.checked } })}
          className="w-4 h-4 text-lucid-600 rounded"
        />
        <label className="text-sm font-medium text-gray-700">Enable Stroke</label>
      </div>

      {/* Apply Button */}
      <button
        onClick={onApply}
        disabled={loading}
        className="w-full py-2 bg-lucid-600 text-white font-medium rounded-lg hover:bg-lucid-700 disabled:opacity-50 transition-colors"
      >
        {loading ? 'Applying...' : 'Apply to This Slide'}
      </button>
    </div>
  );
}
