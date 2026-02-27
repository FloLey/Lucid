import { useState, Component } from 'react';
import type { ReactNode, ErrorInfo } from 'react';
import { ProjectProvider, useProject } from './contexts/ProjectContext';
import { MatrixProvider, useMatrix } from './contexts/MatrixContext';
import StageResearch from './components/StageResearch';
import StageDraft from './components/StageDraft';
import StageStyle from './components/StageStyle';
import StagePrompts from './components/StagePrompts';
import StageImages from './components/StageImages';
import StageTypography from './components/StageTypography';
import Header from './components/Header';
import StageIndicator from './components/StageIndicator';
import ProjectHome from './components/ProjectHome';
import NewProjectModal from './components/NewProjectModal';
import TemplatesPage from './components/TemplatesPage';
import MatrixHome from './components/matrix/MatrixHome';
import MatrixView from './components/matrix/MatrixView';
import MatrixSettingsPage from './components/matrix/MatrixSettings';
import { useDarkMode } from './hooks/useDarkMode';

class ErrorBoundary extends Component<
  { children: ReactNode },
  { hasError: boolean; message: string }
> {
  state = { hasError: false, message: '' };

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, message: error.message };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Unhandled render error:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="h-screen flex items-center justify-center flex-col gap-4 p-8 text-center">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Something went wrong</h1>
          <p className="text-gray-500 dark:text-gray-400 max-w-md">{this.state.message}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-lucid-600 text-white rounded-lg hover:bg-lucid-700"
          >
            Reload
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

type ActiveSection = 'carousel' | 'matrix';

function MatrixSection({ onBack, isDark, onToggleDark }: { onBack: () => void; isDark: boolean; onToggleDark: () => void }) {
  const { currentMatrix, closeMatrix } = useMatrix();
  const [showSettings, setShowSettings] = useState(false);

  if (showSettings) {
    return (
      <div className="h-screen flex flex-col overflow-hidden">
        <Header
          projectName="Matrix Settings"
          onBack={() => setShowSettings(false)}
          isDark={isDark}
          onToggleDark={onToggleDark}
        />
        <main className="flex-1 min-h-0 overflow-y-auto">
          <MatrixSettingsPage onBack={() => setShowSettings(false)} />
        </main>
      </div>
    );
  }

  if (currentMatrix) {
    return (
      <div className="h-screen flex flex-col overflow-hidden">
        <Header
          projectName={currentMatrix.name || currentMatrix.theme}
          onBack={closeMatrix}
          isDark={isDark}
          onToggleDark={onToggleDark}
        />
        <main className="flex-1 min-h-0 overflow-y-auto">
          <MatrixView matrix={currentMatrix} />
        </main>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      <Header
        projectName={null}
        onBack={onBack}
        isDark={isDark}
        onToggleDark={onToggleDark}
      />
      <main className="flex-1 min-h-0 overflow-y-auto">
        <MatrixHome onOpenSettings={() => setShowSettings(true)} />
      </main>
    </div>
  );
}

function AppContent() {
  const {
    projects,
    projectsLoading,
    currentProject,
    error,
    setError,
    openProject,
    closeProject,
    createNewProject,
    deleteProject,
    goToStage,
    renameCurrentProject,
    generateProjectTitle,
  } = useProject();

  const { isDark, toggle: toggleDark } = useDarkMode();
  const [activeSection, setActiveSection] = useState<ActiveSection>('carousel');
  const [showNewProjectModal, setShowNewProjectModal] = useState(false);
  const [showTemplatesPage, setShowTemplatesPage] = useState(false);
  const [isGeneratingName, setIsGeneratingName] = useState(false);

  const currentStage = currentProject?.current_stage ?? 1;
  const hasSlides = (currentProject?.slides?.length ?? 0) > 0;

  const handleGenerateName = async () => {
    setIsGeneratingName(true);
    try {
      await generateProjectTitle();
    } finally {
      setIsGeneratingName(false);
    }
  };

  const renderCurrentStage = () => {
    switch (currentStage) {
      case 1: return <StageResearch />;
      case 2: return <StageDraft />;
      case 3: return <StageStyle />;
      case 4: return <StagePrompts />;
      case 5: return <StageImages />;
      case 6: return <StageTypography />;
      default: return <StageResearch />;
    }
  };

  if (activeSection === 'matrix') {
    return (
      <MatrixProvider>
        <MatrixSection
          onBack={() => setActiveSection('carousel')}
          isDark={isDark}
          onToggleDark={toggleDark}
        />
      </MatrixProvider>
    );
  }

  return (
    <>
      <div className="h-screen flex flex-col overflow-hidden">
        <Header
          projectName={currentProject?.name ?? null}
          onBack={currentProject ? closeProject : null}
          isDark={isDark}
          onToggleDark={toggleDark}
          onRename={currentProject ? renameCurrentProject : undefined}
          onGenerateName={currentProject ? handleGenerateName : undefined}
          canGenerateName={hasSlides}
          isGeneratingName={isGeneratingName}
        />

        {currentProject && (
          <StageIndicator currentStage={currentStage} onStageClick={goToStage} />
        )}

        <main className="flex-1 min-h-0 overflow-y-auto">
          {error && (
            <div className="mx-4 mt-4 p-4 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded-lg">
              {error}
              <button
                onClick={() => setError(null)}
                className="ml-2 text-red-500 hover:text-red-700 dark:text-red-400 dark:hover:text-red-200"
              >
                Dismiss
              </button>
            </div>
          )}

          {currentProject ? (
            <div className="px-4 py-6">
              <div className="max-w-6xl mx-auto">
                {renderCurrentStage()}
              </div>
            </div>
          ) : (
            <ProjectHome
              projects={projects}
              loading={projectsLoading}
              onOpen={openProject}
              onNewProject={() => setShowNewProjectModal(true)}
              onDelete={deleteProject}
              onTemplates={() => setShowTemplatesPage(true)}
              onMatrix={() => setActiveSection('matrix')}
            />
          )}
        </main>
      </div>

      {showNewProjectModal && (
        <NewProjectModal
          onClose={() => setShowNewProjectModal(false)}
          onCreate={async (templateId) => {
            await createNewProject(templateId);
            setShowNewProjectModal(false);
          }}
        />
      )}

      {showTemplatesPage && (
        <TemplatesPage onClose={() => setShowTemplatesPage(false)} />
      )}
    </>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <ProjectProvider>
        <AppContent />
      </ProjectProvider>
    </ErrorBoundary>
  );
}

export default App;
