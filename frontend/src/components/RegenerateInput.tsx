interface RegenerateInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  onCancel: () => void;
  disabled?: boolean;
  placeholder?: string;
}

export default function RegenerateInput({
  value,
  onChange,
  onSubmit,
  onCancel,
  disabled = false,
  placeholder = 'Instruction (optional), Enter to regenerate',
}: RegenerateInputProps) {
  return (
    <div className="mb-2 flex gap-2">
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') onSubmit();
          if (e.key === 'Escape') onCancel();
        }}
        placeholder={placeholder}
        disabled={disabled}
        className="flex-1 px-2 py-1 text-xs border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-lucid-500"
        autoFocus
      />
      <button
        onClick={onSubmit}
        disabled={disabled}
        className="px-2 py-1 text-xs bg-lucid-600 text-white rounded-lg hover:bg-lucid-700 disabled:opacity-50"
      >
        Go
      </button>
    </div>
  );
}
