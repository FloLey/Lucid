import { useState, useMemo } from 'react';
import { useSession } from './hooks/useSession';
import { SessionContext } from './contexts/SessionContext';
import Stage1 from './components/Stage1';
import Stage2 from './components/Stage2';
import Stage3 from './components/Stage3';
import Stage4 from './components/Stage4';
import Stage5 from './components/Stage5';
import Header from './components/Header';
import StageIndicator from './components/StageIndicator';
import ConfigSettings from './components/ConfigSettings';

function App() {
  const {
    sessionId,
    session,
    stageLoading,
    error,
    setStageLoading,
    setError,
    updateSession,
    advanceStage,
    previousStage,
    goToStage,
    startNewSession,
  } = useSession();

  const [showSettings, setShowSettings] = useState(false);

  const currentStage = session?.current_stage ?? 1;

  const sessionContextValue = useMemo(() => ({
    sessionId,
    session,
    loading: stageLoading,
    setLoading: setStageLoading,
    setError,
    updateSession,
    onNext: advanceStage,
    onBack: previousStage,
  }), [sessionId, session, stageLoading, setStageLoading, setError, updateSession, advanceStage, previousStage]);

  const renderCurrentStage = () => {
    switch (currentStage) {
      case 1:
        return <Stage1 />;
      case 2:
        return <Stage2 />;
      case 3:
        return <Stage3 />;
      case 4:
        return <Stage4 />;
      case 5:
        return <Stage5 />;
      default:
        return <Stage1 />;
    }
  };

  return (
    <>
      <div className="h-screen flex flex-col overflow-hidden">
        <Header onNewSession={startNewSession} onSettings={() => setShowSettings(true)} />

        <StageIndicator currentStage={currentStage} onStageClick={goToStage} />

        <main className="flex-1 min-h-0 px-4 py-6 overflow-y-auto">
          <div className="max-w-6xl mx-auto">
            {error && (
              <div className="mb-4 p-4 bg-red-100 text-red-700 rounded-lg">
                {error}
                <button
                  onClick={() => setError(null)}
                  className="ml-2 text-red-500 hover:text-red-700"
                >
                  Dismiss
                </button>
              </div>
            )}

            {session ? (
              <SessionContext.Provider value={sessionContextValue}>
                {renderCurrentStage()}
              </SessionContext.Provider>
            ) : (
              <div className="flex items-center justify-center h-64">
                <div className="text-gray-500">Loading session...</div>
              </div>
            )}
          </div>
        </main>
      </div>

      {showSettings && (
        <ConfigSettings onClose={() => setShowSettings(false)} />
      )}
    </>
  );
}

export default App;
