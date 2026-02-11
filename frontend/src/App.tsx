import { useState } from 'react';
import { useSession } from './hooks/useSession';
import Stage1 from './components/Stage1';
import Stage2 from './components/Stage2';
import Stage3 from './components/Stage3';
import Stage4 from './components/Stage4';
import Stage5 from './components/Stage5';
import Header from './components/Header';
import StageIndicator from './components/StageIndicator';
import ConfigSettings from './components/ConfigSettings';
import ChatPanel from './components/ChatPanel';

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

  const renderCurrentStage = () => {
    const commonProps = {
      sessionId,
      session,
      stageLoading,
      setStageLoading,
      setError,
      updateSession,
      onNext: advanceStage,
      onBack: previousStage,
    };

    switch (currentStage) {
      case 1:
        return <Stage1 {...commonProps} />;
      case 2:
        return <Stage2 {...commonProps} />;
      case 3:
        return <Stage3 {...commonProps} />;
      case 4:
        return <Stage4 {...commonProps} />;
      case 5: {
        const { onNext: _, ...stage5Props } = commonProps;
        return <Stage5 {...stage5Props} />;
      }
      default:
        return <Stage1 {...commonProps} />;
    }
  };

  return (
    <>
      <div className="h-screen flex flex-col overflow-hidden">
        <Header onNewSession={startNewSession} onSettings={() => setShowSettings(true)} />

        <StageIndicator currentStage={currentStage} onStageClick={goToStage} />

        <div className="flex-1 min-h-0 flex">
          {/* Main content area */}
          <main className="flex-1 min-w-0 px-4 py-6 overflow-y-auto">
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
                renderCurrentStage()
              ) : (
                <div className="flex items-center justify-center h-64">
                  <div className="text-gray-500">Loading session...</div>
                </div>
              )}
            </div>
          </main>

          {/* Chat panel (right side, always visible) */}
          {session && (
            <ChatPanel
              sessionId={sessionId}
              currentStage={currentStage}
              updateSession={updateSession}
            />
          )}
        </div>
      </div>

      {showSettings && (
        <ConfigSettings onClose={() => setShowSettings(false)} />
      )}
    </>
  );
}

export default App;
