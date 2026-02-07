interface HeaderProps {
  onNewSession: () => void;
}

export default function Header({ onNewSession }: HeaderProps) {
  return (
    <header className="bg-white shadow-sm border-b border-gray-200">
      <div className="container mx-auto px-4 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-lucid-500 to-lucid-700 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-xl">L</span>
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900">Lucid</h1>
            <p className="text-sm text-gray-500">Transform drafts into carousels</p>
          </div>
        </div>

        <button
          onClick={onNewSession}
          className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
        >
          New Session
        </button>
      </div>
    </header>
  );
}
