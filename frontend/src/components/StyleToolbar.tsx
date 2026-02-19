import type { TextStyle } from '../types';
import { FONTS, FONT_SIZES } from '../constants';
import AlignIcon from './AlignIcon';

type SelectedBox = 'title' | 'body';

interface StyleToolbarProps {
  style: TextStyle;
  selectedBox: SelectedBox;
  hasTitle: boolean;
  loading: boolean;
  setSelectedBox: (box: SelectedBox) => void;
  updateLocalStyle: (updates: Record<string, unknown>) => void;
  onApplyToAll: () => void;
}

export default function StyleToolbar({
  style,
  selectedBox,
  hasTitle,
  loading,
  setSelectedBox,
  updateLocalStyle,
  onApplyToAll,
}: StyleToolbarProps) {
  const getActiveFontSize = (): number => {
    return selectedBox === 'title' ? style.font_size_px : style.body_font_size_px;
  };

  const handleFontSizeChange = (size: number) => {
    if (selectedBox === 'title') {
      updateLocalStyle({ font_size_px: size });
    } else {
      updateLocalStyle({ body_font_size_px: size });
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 px-4 py-3">
      <div className="flex flex-wrap items-center gap-3">
        {/* Selected box indicator */}
        {hasTitle && (
          <div className="flex items-center gap-1">
            <span className="text-xs text-gray-500 mr-1">Editing:</span>
            <button
              onClick={() => setSelectedBox('title')}
              className={`px-2 py-1 text-xs rounded font-medium transition-colors ${
                selectedBox === 'title'
                  ? 'bg-blue-100 text-blue-700 ring-1 ring-blue-300'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              Title
            </button>
            <button
              onClick={() => setSelectedBox('body')}
              className={`px-2 py-1 text-xs rounded font-medium transition-colors ${
                selectedBox === 'body'
                  ? 'bg-blue-100 text-blue-700 ring-1 ring-blue-300'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              Body
            </button>
          </div>
        )}

        <div className="w-px h-6 bg-gray-200" />

        {/* Font family */}
        <select
          value={style.font_family}
          onChange={(e) => updateLocalStyle({ font_family: e.target.value })}
          className="text-xs border border-gray-300 rounded px-2 py-1.5 bg-white"
          style={{ fontFamily: style.font_family }}
        >
          {FONTS.map((f) => (
            <option key={f} value={f} style={{ fontFamily: f }}>{f}</option>
          ))}
        </select>

        {/* Font size */}
        <select
          value={getActiveFontSize()}
          onChange={(e) => handleFontSizeChange(Number(e.target.value))}
          className="text-xs border border-gray-300 rounded px-2 py-1.5 bg-white w-16"
        >
          {FONT_SIZES.map((s) => (
            <option key={s} value={s}>{s}px</option>
          ))}
        </select>

        {/* Color picker */}
        <div className="relative">
          <input
            type="color"
            value={style.text_color.slice(0, 7)}
            onChange={(e) => updateLocalStyle({ text_color: e.target.value })}
            className="w-7 h-7 rounded cursor-pointer border border-gray-300"
            title="Text color"
          />
        </div>

        <div className="w-px h-6 bg-gray-200" />

        {/* Alignment */}
        {(['left', 'center', 'right'] as const).map((align) => (
          <button
            key={align}
            onClick={() => updateLocalStyle({ alignment: align })}
            className={`p-1.5 rounded transition-colors ${
              style.alignment === align
                ? 'bg-lucid-100 text-lucid-700'
                : 'text-gray-500 hover:bg-gray-100'
            }`}
            title={`Align ${align}`}
          >
            <AlignIcon align={align} />
          </button>
        ))}

        <div className="w-px h-6 bg-gray-200" />

        {/* Stroke toggle */}
        <button
          onClick={() => updateLocalStyle({ stroke: { enabled: !style.stroke.enabled } })}
          className={`px-2 py-1 text-xs rounded font-medium transition-colors ${
            style.stroke.enabled
              ? 'bg-gray-800 text-white'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
          title="Toggle stroke"
        >
          Stroke
        </button>

        {/* Text visibility toggle */}
        <button
          onClick={() => updateLocalStyle({ text_enabled: !style.text_enabled })}
          className={`px-2 py-1 text-xs rounded font-medium transition-colors ${
            style.text_enabled
              ? 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              : 'bg-orange-100 text-orange-700 ring-1 ring-orange-300'
          }`}
          title={style.text_enabled ? 'Hide text overlay' : 'Show text overlay'}
        >
          {style.text_enabled ? 'Text On' : 'Text Off'}
        </button>

        <div className="flex-1" />

        {/* Apply to All */}
        <button
          onClick={onApplyToAll}
          disabled={loading}
          className="px-3 py-1.5 text-xs bg-white border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
        >
          {loading ? 'Applying...' : 'Apply to All'}
        </button>
      </div>
    </div>
  );
}
