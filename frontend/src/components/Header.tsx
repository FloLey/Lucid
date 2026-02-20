interface HeaderProps {
  projectName: string | null;
  onBack: (() => void) | null;
}

export default function Header({ projectName, onBack }: HeaderProps) {
  return (
    <header className="bg-white shadow-sm border-b border-gray-200">
      <div className="container mx-auto px-4 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          {onBack ? (
            <button
              onClick={onBack}
              className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors"
              title="Back to Projects"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              <span className="text-sm font-medium">Projects</span>
            </button>
          ) : (
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-lucid-500 to-lucid-700 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-xl">L</span>
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">Lucid</h1>
                <p className="text-sm text-gray-500">Transform drafts into carousels</p>
              </div>
            </div>
          )}

          {projectName && (
            <>
              <span className="text-gray-300">/</span>
              <span className="text-sm font-medium text-gray-700 truncate max-w-xs">
                {projectName}
              </span>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
