interface HeaderProps {
  projectName: string | null;
  onBack: (() => void) | null;
  isDark: boolean;
  onToggleDark: () => void;
}

export default function Header({ projectName, onBack, isDark, onToggleDark }: HeaderProps) {
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
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300 truncate max-w-xs">
                {projectName}
              </span>
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
