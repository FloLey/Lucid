import { useState } from 'react';
import { useSession } from './hooks/useSession';
import Stage1 from './components/Stage1';
import Stage2 from './components/Stage2';
import Stage3 from './components/Stage3';
import Stage4 from './components/Stage4';
import ChatBar from './components/ChatBar';
import Header from './components/Header';
import StageIndicator from './components/StageIndicator';

function App() {
  const {
    sessionId,
    session,
    loading,
    error,
    setLoading,
    setError,
    updateSession,
    advanceStage,
    startNewSession,
  } = useSession();

  const [chatOpen, setChatOpen] = useState(false);

  const currentStage = session?.current_stage ?? 1;

  const renderCurrentStage = () => {
    const commonProps = {
      sessionId,
      session,
      loading,
      setLoading,
      setError,
      updateSession,
      onNext: advanceStage,
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
      default:
        return <Stage1 {...commonProps} />;
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Header onNewSession={startNewSession} />

      <StageIndicator currentStage={currentStage} />

      <main className="flex-1 container mx-auto px-4 py-6">
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
      </main>

      <ChatBar
        sessionId={sessionId}
        isOpen={chatOpen}
        onToggle={() => setChatOpen(!chatOpen)}
        updateSession={updateSession}
      />
    </div>
  );
}

export default App;
