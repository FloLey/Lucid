import Header from './Header';

interface ModeSelectorProps {
  onSelect: (mode: 'carousel' | 'matrix') => void;
  isDark: boolean;
  onToggleDark: () => void;
}

export default function ModeSelector({ onSelect, isDark, onToggleDark }: ModeSelectorProps) {
  return (
    <div className="h-screen flex flex-col overflow-hidden">
      <Header
        projectName={null}
        onBack={null}
        isDark={isDark}
        onToggleDark={onToggleDark}
      />
      <main className="flex-1 flex flex-col items-center justify-center px-6 py-12">
        <div className="text-center mb-10">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
            What would you like to create?
          </h2>
          <p className="text-gray-500 dark:text-gray-400 mt-2">
            Design polished slide carousels or explore ideas as visual concept matrices.
          </p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 w-full max-w-2xl">
          <button
            onClick={() => onSelect('carousel')}
            className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-8 text-center hover:shadow-md hover:border-lucid-300 dark:hover:border-lucid-600 transition-all"
          >
            <div className="flex justify-center mb-4">
              <div className="w-16 h-16 bg-lucid-50 dark:bg-lucid-900/30 rounded-2xl flex items-center justify-center">
                <svg className="w-8 h-8 text-lucid-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                </svg>
              </div>
            </div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
              Slide Generation
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Turn rough drafts into polished social media carousels, stage by stage.
            </p>
          </button>

          <button
            onClick={() => onSelect('matrix')}
            className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-8 text-center hover:shadow-md hover:border-lucid-300 dark:hover:border-lucid-600 transition-all"
          >
            <div className="flex justify-center mb-4">
              <div className="w-16 h-16 bg-lucid-50 dark:bg-lucid-900/30 rounded-2xl flex items-center justify-center">
                <svg className="w-8 h-8 text-lucid-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 5a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H5a1 1 0 01-1-1V5zm10 0a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1V5zM4 15a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H5a1 1 0 01-1-1v-4zm10 0a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
                </svg>
              </div>
            </div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
              Matrix Generation
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Generate n×n concept matrices to explore interconnected ideas.
            </p>
          </button>
        </div>
      </main>
    </div>
  );
}
