import { useState, useRef, useEffect } from 'react';

interface HeaderProps {
  projectName: string | null;
  onBack: (() => void) | null;
  isDark: boolean;
  onToggleDark: () => void;
  onRename?: (name: string) => void;
  onGenerateName?: () => void;
  canGenerateName?: boolean;
  isGeneratingName?: boolean;
}

export default function Header({
  projectName,
  onBack,
  isDark,
  onToggleDark,
  onRename,
  onGenerateName,
  canGenerateName = false,
  isGeneratingName = false,
}: HeaderProps) {
  const [editing, setEditing] = useState(false);
  const [editValue, setEditValue] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const startEdit = () => {
    if (!onRename || !projectName) return;
    setEditValue(projectName);
    setEditing(true);
  };

  useEffect(() => {
    if (editing) {
      inputRef.current?.focus();
      inputRef.current?.select();
    }
  }, [editing]);

  const commitEdit = () => {
    const trimmed = editValue.trim();
    if (trimmed && trimmed !== projectName && onRename) {
      onRename(trimmed);
    }
    setEditing(false);
  };

  const cancelEdit = () => {
    setEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') commitEdit();
    if (e.key === 'Escape') cancelEdit();
  };

  return (
    <header className="bg-white dark:bg-gray-900 shadow-sm border-b border-gray-200 dark:border-gray-700">
      <div className="container mx-auto px-4 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3 min-w-0">
          {onBack ? (
            <button
              onClick={onBack}
              className="flex items-center gap-2 text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white transition-colors flex-shrink-0"
              title="Back to Projects"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              <span className="text-sm font-medium">Projects</span>
            </button>
          ) : (
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-lucid-500 to-lucid-700 rounded-lg flex items-center justify-center flex-shrink-0">
                <span className="text-white font-bold text-xl">L</span>
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900 dark:text-white">Lucid</h1>
                <p className="text-sm text-gray-500 dark:text-gray-400">Transform drafts into carousels</p>
              </div>
            </div>
          )}

          {projectName && (
            <>
              <span className="text-gray-300 dark:text-gray-600 flex-shrink-0">/</span>
              {editing ? (
                <input
                  ref={inputRef}
                  value={editValue}
                  onChange={(e) => setEditValue(e.target.value)}
                  onBlur={commitEdit}
                  onKeyDown={handleKeyDown}
                  className="text-sm font-medium text-gray-900 dark:text-gray-100 bg-white dark:bg-gray-800 border border-lucid-400 rounded px-2 py-0.5 focus:outline-none focus:ring-2 focus:ring-lucid-500 w-56 max-w-xs"
                />
              ) : (
                <span className="flex items-center gap-1.5 min-w-0">
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300 truncate max-w-xs">
                    {projectName}
                  </span>
                  {onRename && (
                    <button
                      onClick={startEdit}
                      title="Rename project"
                      className="flex-shrink-0 p-0.5 rounded text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors"
                    >
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                          d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                      </svg>
                    </button>
                  )}
                  {onGenerateName && canGenerateName && (
                    <button
                      onClick={onGenerateName}
                      disabled={isGeneratingName}
                      title="Generate name from slide content"
                      className="flex-shrink-0 flex items-center gap-1 px-1.5 py-0.5 rounded text-xs text-gray-400 hover:text-lucid-600 dark:hover:text-lucid-400 hover:bg-lucid-50 dark:hover:bg-lucid-900/20 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                    >
                      {isGeneratingName ? (
                        <svg className="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                      ) : (
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                            d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                      )}
                      <span>AI name</span>
                    </button>
                  )}
                </span>
              )}
            </>
          )}
        </div>

        {/* Dark mode toggle */}
        <button
          onClick={onToggleDark}
          title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
          className="p-2 rounded-lg text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors flex-shrink-0"
        >
          {isDark ? (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707M17.657 17.657l-.707-.707M6.343 6.343l-.707-.707M12 7a5 5 0 100 10A5 5 0 0012 7z" />
            </svg>
          ) : (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M21 12.79A9 9 0 1111.21 3a7 7 0 009.79 9.79z" />
            </svg>
          )}
        </button>
      </div>
    </header>
  );
}
